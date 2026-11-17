import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import FrontendLaunchDescriptionSource


def generate_launch_description():
    astra_share = get_package_share_directory('astra_camera')
    astra_prefix = os.path.normpath(os.path.join(astra_share, '..', '..'))
    astra_lib = os.path.join(astra_prefix, 'lib')
    astra_drivers = os.path.join(astra_lib, 'OpenNI2', 'Drivers')
    current_library_path = os.environ.get('LD_LIBRARY_PATH', '')

    set_openni_redist = SetEnvironmentVariable(
        'OPENNI2_REDIST',
        astra_lib,
    )
    set_library_path = SetEnvironmentVariable(
        'LD_LIBRARY_PATH',
        os.pathsep.join([
            astra_lib,
            astra_drivers,
            current_library_path,
        ]),
    )

    astra = IncludeLaunchDescription(
        FrontendLaunchDescriptionSource([
            os.path.join(
                astra_share,
                'launch',
                'astro_pro_plus.launch.xml',
            )
        ]),
        launch_arguments={
            'depth_registration': 'true',
            'enable_colored_point_cloud': 'true',
            'publish_tf': 'true',
        }.items(),
    )

    return LaunchDescription([
        set_openni_redist,
        set_library_path,
        astra,
    ])
