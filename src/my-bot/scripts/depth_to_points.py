#!/usr/bin/python3

import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image, PointCloud2, PointField


class DepthToPointCloud(Node):
    def __init__(self):
        super().__init__('depth_to_points')

        self.declare_parameter(
            'depth_topic',
            '/camera/depth/image_raw',
        )
        self.declare_parameter(
            'camera_info_topic',
            '/camera/depth/camera_info',
        )
        self.declare_parameter(
            'output_topic',
            '/camera/depth_registered/points',
        )
        self.declare_parameter(
            'color_topic',
            '/camera/image_raw',
        )
        self.declare_parameter('pixel_step', 8)
        self.declare_parameter('min_depth', 0.05)
        self.declare_parameter('max_depth', 8.0)
        self.declare_parameter('horizontal_fov', 1.089)

        self.bridge = CvBridge()
        self.color_image = None
        self.fx = None
        self.fy = None
        self.cx = None
        self.cy = None

        self.publisher = self.create_publisher(
            PointCloud2,
            self.get_parameter('output_topic').value,
            10,
        )
        self.create_subscription(
            CameraInfo,
            self.get_parameter('camera_info_topic').value,
            self.camera_info_callback,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            Image,
            self.get_parameter('depth_topic').value,
            self.depth_callback,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            Image,
            self.get_parameter('color_topic').value,
            self.color_callback,
            qos_profile_sensor_data,
        )

    def camera_info_callback(self, msg):
        self.fx = msg.k[0]
        self.cx = msg.k[2]
        self.fy = msg.k[4]
        self.cy = msg.k[5]

    def color_callback(self, msg):
        try:
            self.color_image = self.bridge.imgmsg_to_cv2(
                msg,
                desired_encoding='rgb8',
            )
        except Exception as error:
            self.get_logger().warning(
                f'Failed to convert color image: {error}',
            )

    def depth_callback(self, msg):
        if self.fx is None:
            return
        if self.color_image is None:
            return

        try:
            depth = self.bridge.imgmsg_to_cv2(
                msg,
                desired_encoding='passthrough',
            )
        except Exception as error:
            self.get_logger().warning(
                f'Failed to convert depth image: {error}',
            )
            return

        encoding = msg.encoding.lower()
        if encoding == '16uc1':
            depth = depth.astype(np.float32) / 1000.0
        elif encoding == '32fc1':
            depth = depth.astype(np.float32)
        else:
            self.get_logger().warning(
                f'Unsupported depth encoding: {msg.encoding}',
            )
            return

        pixel_step = max(1, int(self.get_parameter('pixel_step').value))
        min_depth = float(self.get_parameter('min_depth').value)
        max_depth = float(self.get_parameter('max_depth').value)

        height, width = depth.shape
        horizontal_fov = float(
            self.get_parameter('horizontal_fov').value
        )
        fx = (width / 2.0) / np.tan(horizontal_fov / 2.0)
        fy = fx
        cx = (width - 1.0) / 2.0
        cy = (height - 1.0) / 2.0

        u = np.arange(0, width, pixel_step)
        v = np.arange(0, height, pixel_step)
        z = depth[np.ix_(v, u)]
        valid = np.isfinite(z) & (z >= min_depth) & (z <= max_depth)

        if not np.any(valid):
            return

        uu, vv = np.meshgrid(u, v)
        z = z[valid]
        x = (uu[valid] - cx) * z / fx
        y = (vv[valid] - cy) * z / fy

        color = self.color_image
        if color.shape[:2] != depth.shape:
            color = np.resize(color, depth.shape + (3,))
        colors = color[np.ix_(v, u)][valid]
        colors = colors.astype(np.uint32)
        rgb = (
            (colors[:, 0] << 16)
            | (colors[:, 1] << 8)
            | colors[:, 2]
        ).view(np.float32)

        points = np.empty((z.shape[0], 4), dtype=np.float32)
        points[:, 0] = x
        points[:, 1] = y
        points[:, 2] = z
        points[:, 3] = rgb

        cloud = PointCloud2()
        cloud.header = msg.header
        cloud.height = 1
        cloud.width = points.shape[0]
        cloud.fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
            PointField(name='rgb', offset=12, datatype=PointField.FLOAT32, count=1),
        ]
        cloud.is_bigendian = False
        cloud.point_step = 16
        cloud.row_step = cloud.point_step * cloud.width
        cloud.is_dense = False
        cloud.data = points.tobytes()
        self.publisher.publish(cloud)


def main(args=None):
    rclpy.init(args=args)
    node = DepthToPointCloud()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        # launch 发 SIGINT 时 rclpy 已经关过 context 了，这里不要再 spin
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
