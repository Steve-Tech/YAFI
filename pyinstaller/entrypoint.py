import os
if os.name == 'nt' and os.environ.get('GDK_SCALE') is None:
    import ctypes
    scale_factor = ctypes.windll.shcore.GetScaleFactorForDevice(0)
    os.environ["GDK_SCALE"] = f"{round(scale_factor, -2)//100}"

from yafi import main
main()
