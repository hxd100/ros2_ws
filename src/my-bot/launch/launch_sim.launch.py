import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            SetEnvironmentVariable)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    package_name = 'my_bot'
    package_share = get_package_share_directory(package_name)
    world_file = os.path.join(package_share, 'worlds', 'empty.world')
    rviz_config = os.path.join(package_share, 'config', 'view_bot.rviz')

    set_ign_ip = SetEnvironmentVariable('IGN_IP', '127.0.0.1')

    # 无界面：追加 -s 只跑 server（没有 X / 远程 SSH 时用）
    gz_args = LaunchConfiguration('gz_args')
    use_rviz = LaunchConfiguration('use_rviz')

    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(
                package_share,
                'launch',
                'rsp.launch.py',
            )
        ]),
        launch_arguments={'use_sim_time': 'true'}.items(),
    )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(
                get_package_share_directory('ros_gz_sim'),
                'launch',
                'gz_sim.launch.py',
            )
        ]),
        launch_arguments={'gz_args': gz_args}.items(),
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/model/my_robot/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist',
            '/model/my_robot/odometry@nav_msgs/msg/Odometry[ignition.msgs.Odometry',
            '/world/empty/model/my_robot/joint_state@sensor_msgs/msg/JointState[ignition.msgs.Model',
            '/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan',
            # 必须桥 /clock，否则 use_sim_time 的节点（slam_toolbox / nav2）
            # 拿到的是墙钟时间，和 TF 时间戳对不上，会一直报
            # "Failed to compute odom pose"
            '/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',
            '/camera/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
            '/camera/depth/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
        ],
        remappings=[
            ('/model/my_robot/cmd_vel', '/cmd_vel'),
            ('/model/my_robot/odometry', '/odom'),
            ('/world/empty/model/my_robot/joint_state', '/joint_states'),
        ],
        output='screen',
    )

    depth_points = Node(
        package='my_bot',
        executable='depth_to_points.py',
        name='depth_to_points',
        parameters=[{'pixel_step': 10, 'use_sim_time': True}],
        output='screen',
    )

    odom_tf = Node(
        package='my_bot',
        executable='odom_to_tf.py',
        name='odom_to_tf',
        # 必须用仿真时间：否则 TF 时间戳是墙钟，
        # slam_toolbox / nav2 按 /clock 查 TF 会一直 "Failed to compute odom pose"
        parameters=[{'use_sim_time': True}],
        output='screen',
    )

    image_bridge = Node(
        package='ros_gz_image',
        executable='image_bridge',
        arguments=[
            '/camera/image_raw',
            '/camera/depth/image_raw',
        ],
        output='screen',
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],
        output='screen',
        condition=IfCondition(use_rviz),
    )

    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-topic',
            '/robot_description',
            '-name',
            'my_robot',
        ],
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'gz_args', default_value=f'-r {world_file}',
            description='Gazebo 参数；无界面用 "-r -s <world>"'),
        DeclareLaunchArgument(
            'use_rviz', default_value='true',
            description='是否启动 RViz（无 X 时设 false）'),
        set_ign_ip,
        rsp,
        gazebo,
        bridge,
        image_bridge,
        depth_points,
        odom_tf,
        spawn_entity,
        rviz,
    ])
