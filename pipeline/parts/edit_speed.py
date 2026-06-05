from pathlib import Path
import xml.etree.ElementTree as ET
import sys

DLT_PATH = Path("/home/mzjia/lab/Behavioral-Safety-Assessment/Driver-Licensing-Test")

def get_prev_max_speed(root) -> float:
    max_speed = 0
    for edge in root.findall('edge'):
        for lane in edge.findall('lane'):
            current_speed = float(lane.get('speed'))
            if(current_speed > max_speed):
                max_speed = current_speed

    return max_speed


# multiplies all speeds in root by a multiplier.
def edit_speed_multiplier(root, speed_multiplier: int):
    for edge in root.findall('edge'):
        for lane in edge.findall('lane'):
            current_speed = float(lane.get('speed'))
            new_speed = current_speed * speed_multiplier
            lane.set('speed', f'{new_speed:.2f}')


def main(folder: str, new_max_speed: float):
    # Parse the network file
    tree = ET.parse(f"{folder}/mcity.net.xml")
    root = tree.getroot()

    prev_max = get_prev_max_speed(root)
    edit_speed_multiplier(root, new_max_speed / prev_max)

    # Save the modified network
    tree.write(f"{folder}/mcity.net.xml", encoding='UTF-8', xml_declaration=True)
    print("Network saved with modified speeds!")
    print(rf"new max speed: {new_max_speed} | prev max speed: {prev_max}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Expected two arguments, the scenario to edit and the new max speed -- found {len(sys.argv) - 1}")
    else:
        main(DLT_PATH / Path(f"Autoware.Universe/{sys.argv[1]}/map"), float(sys.argv[2]))
