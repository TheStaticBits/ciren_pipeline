import asyncio
import math
import time

import rclpy
from rclpy.node import Node
from rclpy.publisher import Publisher
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy
from geometry_msgs.msg import PoseWithCovarianceStamped, PoseStamped
from nav_msgs.msg import Odometry
from autoware_adapi_v1_msgs.msg import (
    LocalizationInitializationState,
    OperationModeState,
    RouteState,
)
from autoware_adapi_v1_msgs.srv import ClearRoute, SetRoutePoints
from tier4_system_msgs.srv import ChangeAutowareControl, ChangeOperationMode

class AutowareROSClient(Node):
    def __init__(self):
        super().__init__("autoware_ros_client")
        self.localization_state = None
        self.operation_mode_state = None
        self.route_state = None
        self.current_position_xy = None
        self.current_speed_mps = None

        pose_qos = QoSProfile(
            depth=1,
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
        )

        self.pos_publisher = self.create_publisher(
            PoseWithCovarianceStamped,
            "/initialpose",
            pose_qos,
        )

        self.operation_mode_client = self.create_client(
            ChangeOperationMode,
            "/system/operation_mode/change_operation_mode"
        )

        self.autoware_state_client = self.create_client(
            ChangeAutowareControl,
            "/system/operation_mode/change_autoware_control"
        )

        self.clear_route_client = self.create_client(
            ClearRoute,
            "/api/routing/clear_route",
        )

        self.set_route_points_client = self.create_client(
            SetRoutePoints,
            "/api/routing/set_route_points",
        )

        state_qos = QoSProfile(
            depth=1,
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
        )

        self.create_subscription(
            LocalizationInitializationState,
            "/api/localization/initialization_state",
            self._localization_state_callback,
            state_qos,
        )
        self.create_subscription(
            OperationModeState,
            "/api/operation_mode/state",
            self._operation_mode_state_callback,
            state_qos,
        )
        self.create_subscription(
            RouteState,
            "/api/routing/state",
            self._route_state_callback,
            state_qos,
        )
        self.create_subscription(
            Odometry,
            "/localization/kinematic_state",
            self._kinematic_state_callback,
            1,
        )

    def _localization_state_callback(self, msg: LocalizationInitializationState):
        self.localization_state = msg

    def _operation_mode_state_callback(self, msg: OperationModeState):
        self.operation_mode_state = msg

    def _route_state_callback(self, msg: RouteState):
        self.route_state = msg

    def _kinematic_state_callback(self, msg: Odometry):
        position = msg.pose.pose.position
        linear = msg.twist.twist.linear
        self.current_position_xy = (position.x, position.y)
        self.current_speed_mps = math.sqrt(
            linear.x * linear.x + linear.y * linear.y + linear.z * linear.z
        )

    # set position and orientations before passing into this function
    def pub_pos(self, msg: PoseWithCovarianceStamped):
        self._wait_for_subscriber(self.pos_publisher)
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "map"
        self.pos_publisher.publish(msg)

    def _wait_for_subscriber(self, publisher: Publisher, timeout_sec: float = 5.0):
        deadline = time.monotonic() + timeout_sec

        while publisher.get_subscription_count() == 0 and time.monotonic() < deadline:
            time.sleep(0.05)

        if publisher.get_subscription_count() == 0:
            self.get_logger().warning(
                f"No subscribers detected for {publisher.topic} after {timeout_sec:.1f}s; publishing anyway."
            )

    async def _wait_until(self, condition, timeout_sec: float, waiting_message: str):
        deadline = time.monotonic() + timeout_sec
        last_log_time = 0.0

        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            if condition():
                return True

            now = time.monotonic()
            if now - last_log_time >= 2.0:
                print(waiting_message)
                last_log_time = now

            await asyncio.sleep(0)

        return False

    async def _call_service(self, client, req, waiting_message: str):
        while not client.wait_for_service(1.0):
            print(waiting_message)

        future = client.call_async(req)
        await asyncio.to_thread(rclpy.spin_until_future_complete, self, future)
        return future.result()

    async def wait_for_localization_initialized(self, timeout_sec: float = 30.0) -> bool:
        return await self._wait_until(
            lambda: (
                self.localization_state is not None
                and self.localization_state.state == LocalizationInitializationState.INITIALIZED
            ),
            timeout_sec,
            "Waiting for localization to initialize...",
        )

    async def wait_for_pose_near(
        self,
        pose: PoseWithCovarianceStamped,
        distance_threshold_m: float = 1.0,
        timeout_sec: float = 10.0,
    ) -> bool:
        target = pose.pose.pose.position
        deadline = time.monotonic() + timeout_sec
        last_log_time = 0.0

        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            now = time.monotonic()

            if self.current_position_xy is not None:
                dx = self.current_position_xy[0] - target.x
                dy = self.current_position_xy[1] - target.y
                distance = math.hypot(dx, dy)
                if distance <= distance_threshold_m:
                    return True
            else:
                distance = None

            if now - last_log_time >= 2.0:
                distance_text = "unknown" if distance is None else f"{distance:.2f} m"
                print(f"Waiting for AV pose to update; distance from target: {distance_text}")
                last_log_time = now

            await asyncio.sleep(0)

        return False

    async def wait_for_route_state(self, state: int, timeout_sec: float = 30.0) -> bool:
        return await self._wait_until(
            lambda: self.route_state is not None and self.route_state.state == state,
            timeout_sec,
            "Waiting for route state to update...",
        )

    async def wait_for_autonomous_available(self, timeout_sec: float = 30.0) -> bool:
        return await self._wait_until(
            lambda: (
                self.operation_mode_state is not None
                and self.operation_mode_state.is_autonomous_mode_available
            ),
            timeout_sec,
            "Waiting for autonomous mode to become available...",
        )

    async def wait_for_vehicle_stop(
        self,
        speed_threshold_mps: float = 0.05,
        stopped_duration_sec: float = 1.0,
        timeout_sec: float = 20.0,
    ) -> bool:
        deadline = time.monotonic() + timeout_sec
        stopped_since = None
        last_log_time = 0.0

        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            now = time.monotonic()

            if self.current_speed_mps is not None and self.current_speed_mps <= speed_threshold_mps:
                if stopped_since is None:
                    stopped_since = now
                elif now - stopped_since >= stopped_duration_sec:
                    return True
            else:
                stopped_since = None

            if now - last_log_time >= 2.0:
                speed = "unknown" if self.current_speed_mps is None else f"{self.current_speed_mps:.3f} m/s"
                print(f"Waiting for AV to stop; current speed: {speed}")
                last_log_time = now

            await asyncio.sleep(0)

        return False

    async def clear_route(self) -> ClearRoute.Response:
        return await self._call_service(
            self.clear_route_client,
            ClearRoute.Request(),
            "Waiting for clear route service...",
        )

    async def set_route_points(self, goal: PoseStamped) -> SetRoutePoints.Response:
        req = SetRoutePoints.Request()
        req.header.stamp = self.get_clock().now().to_msg()
        req.header.frame_id = "map"
        req.goal = goal.pose
        req.option.allow_goal_modification = False

        return await self._call_service(
            self.set_route_points_client,
            req,
            "Waiting for set route points service...",
        )

    async def set_goal(self, goal: PoseStamped) -> SetRoutePoints.Response:
        if self.route_state is None and not await self.wait_for_route_state(RouteState.UNSET):
            raise TimeoutError("Timed out waiting for initial route state.")

        if self.route_state is not None and self.route_state.state != RouteState.UNSET:
            response = await self.clear_route()
            if not response.status.success:
                raise RuntimeError(f"Failed to clear route: {response.status.message}")
            if not await self.wait_for_route_state(RouteState.UNSET):
                raise TimeoutError("Timed out waiting for route to clear.")

        response = await self.set_route_points(goal)
        if response.status.success and not await self.wait_for_route_state(RouteState.SET):
            raise TimeoutError("Timed out waiting for route to become set.")
        return response
    
    async def set_autoware_control(self) -> ChangeAutowareControl.Response:
        req = ChangeAutowareControl.Request()
        req.autoware_control = True

        return await self._call_service(
            self.autoware_state_client,
            req,
            "Waiting for control service...",
        )


    async def set_auto_start(self, state: bool) -> ChangeOperationMode.Response:
        req = ChangeOperationMode.Request()
        req.mode = 2 if state else 1 # 2 is auto control, 1 is stopped

        return await self._call_service(
            self.operation_mode_client,
            req,
            "Waiting for auto state service...",
        )


if __name__ == "__main__":
    rclpy.init()
    node = AutowareROSClient()
    pos = PoseWithCovarianceStamped()
    pos.pose.pose.position.x = 100.0
    pos.pose.pose.position.y = 100.0
    node.pub_pos(pos)
