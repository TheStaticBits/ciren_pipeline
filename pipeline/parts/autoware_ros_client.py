import asyncio
import time

import rclpy
from rclpy.node import Node
from rclpy.publisher import Publisher
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy
from geometry_msgs.msg import PoseWithCovarianceStamped, PoseStamped
from tier4_system_msgs.srv import ChangeAutowareControl, ChangeOperationMode

class AutowareROSClient(Node):
    def __init__(self):
        super().__init__("autoware_ros_client")

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

        self.pos_goal_publisher = self.create_publisher(
            PoseStamped,
            "/planning/mission_planning/goal",
            pose_qos,
        )

        self.operation_mode_client = self.create_client(
            ChangeOperationMode,
            "/system/operation/mode/change_operation_mode"
        )

        self.autoware_state_client = self.create_client(
            ChangeAutowareControl,
            "/system/operation_mode/change_autoware_control"
        )

    # set position and orientations before passing into this function
    def pub_pos(self, msg: PoseWithCovarianceStamped):
        self._wait_for_subscriber(self.pos_publisher)
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "map"
        self.pos_publisher.publish(msg)
        
    def pub_goal(self, msg: PoseStamped):
        self._wait_for_subscriber(self.pos_goal_publisher)
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "map"
        self.pos_goal_publisher.publish(msg)

    def _wait_for_subscriber(self, publisher: Publisher, timeout_sec: float = 5.0):
        deadline = time.monotonic() + timeout_sec

        while publisher.get_subscription_count() == 0 and time.monotonic() < deadline:
            time.sleep(0.05)

        if publisher.get_subscription_count() == 0:
            self.get_logger().warning(
                f"No subscribers detected for {publisher.topic} after {timeout_sec:.1f}s; publishing anyway."
            )

    async def _call_service(self, client, req, waiting_message: str):
        while not client.wait_for_service(1.0):
            print(waiting_message)

        future = client.call_async(req)
        await asyncio.to_thread(rclpy.spin_until_future_complete, self, future)
        return future.result()
    
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