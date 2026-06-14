from pathlib import Path
import xml.etree.ElementTree as ET
import sys

DLT_PATH = Path("/home/mzjia/lab/Behavioral-Safety-Assessment/Driver-Licensing-Test/env/route")
NET_FILE = "mcity.net.xml"
BACKUP_NET_FILE = "mcity.net.original.xml"

def get_prev_max_speed(root) -> float:
    max_speed = 0
    for edge in root.findall('edge'):
        for lane in edge.findall('lane'):
            speed = lane.get('speed')
            if speed is None:
                continue

            current_speed = float(speed)
            if(current_speed > max_speed):
                max_speed = current_speed

    return max_speed


# multiplies all speeds in root by a multiplier.
def edit_speed_multiplier(root, speed_multiplier: int):
    for edge in root.findall('edge'):
        for lane in edge.findall('lane'):
            speed = lane.get('speed')
            if speed is None:
                continue

            current_speed = float(speed)
            new_speed = current_speed * speed_multiplier
            lane.set('speed', f'{new_speed:.2f}')


def main(folder: str, new_max_speed: float):
    folder = Path(folder)
    net_path = folder / NET_FILE
    backup_net_path = folder / BACKUP_NET_FILE

    if new_max_speed <= 0:
        print(f"[WARNING] Skipping speed edit for non-positive max speed: {new_max_speed}")
        return

    if not backup_net_path.exists():
        backup_net_path.write_bytes(net_path.read_bytes())

    # Parse the network file
    tree = ET.parse(backup_net_path)
    root = tree.getroot()

    prev_max = get_prev_max_speed(root)
    if prev_max == 0:
        raise ValueError(f"Cannot scale speeds in {backup_net_path}: max original speed is 0.")

    edit_speed_multiplier(root, new_max_speed / prev_max)

    # Save the modified network
    tree.write(net_path, encoding='UTF-8', xml_declaration=True)
    print("Network saved with modified speeds!")
    print(rf"new max speed: {new_max_speed} | prev max speed: {prev_max}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Expected two arguments, the scenario to edit and the new max speed -- found {len(sys.argv) - 1}")
    else:
        main(DLT_PATH / Path(f"Autoware.Universe/{sys.argv[1]}/map"), float(sys.argv[2]))
