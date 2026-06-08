import rclpy, asyncio
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped
from tier4_system_msgs.srv import ChangeAutowareControl, ChangeOperationMode

class AutowareROSClient(Node):
    def __init__(self):
        super().__init__("autoware_ros_client")

        self.pos_publisher = self.create_publisher(
            PoseWithCovarianceStamped,
            "/initialpose",
            10
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
        msg.header.stamp = self.get_clock().now()
        msg.header.frame_id = "map"
        self.pos_publisher.publish(msg)
    
    async def set_autoware_control(self) -> ChangeAutowareControl.Response:
        req = ChangeAutowareControl.Request
        req.autoware_control = True

        while (not self.autoware_state_client.wait_for_service(1)):
            print("Waiting for control service...")
        
        return await self.autoware_state_client.call_async(req)


    async def set_auto_start(self, state: bool) -> ChangeAutowareControl.Response:
        req = ChangeAutowareControl.Request
        req.mode = 2 if state else 1 # 2 is auto control, 1 is stopped

        while (not self.autoware_state_client.wait_for_service(1)):
            print("Waiting for auto state service...")
        
        return await self.operation_mode_client.call_async(req)