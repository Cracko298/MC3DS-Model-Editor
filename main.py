import sys, shutil, os, random, string, json, re, time, zipfile, io
from tkinter import ttk, messagebox, filedialog
import tkinter as tk
VERSION = 0.31


try:
    import stl
    import numpy as np
    import requests
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from modules import bjson, conversions, JOAAThash, updateDatabase
except ImportError:
    os.system(f'pip install -r "{os.path.dirname(__file__)}\\requirements.txt"')
    messagebox.showinfo("Notice","The script has installed some python Modules.\nIt will now restart and attempt to boot.")
    time.sleep(1)
    os.system(f'python "{os.path.dirname(__file__)}\\main.py"')
    sys.exit(1)

class Object3D:
    def __init__(self, name, position, dimensions):
        self.name = name
        self.position = np.array(position)
        self.dimensions = np.array(dimensions)
        self.selected = False
        self.texture = None

    def get_corners(self):
        x, y, z = self.position
        dx, dy, dz = self.dimensions
        return [
            [x, y, z],
            [x + dx, y, z],
            [x + dx, y + dy, z],
            [x, y + dy, z],
            [x, y, z + dz],
            [x + dx, y, z + dz],
            [x + dx, y + dy, z + dz],
            [x, y + dy, z + dz],
        ]
    
    def scale(self, scale_factor):
        self.dimensions *= scale_factor

    def reset_scale(self):  # Not used
        self.dimensions = self.original_dimensions


def map_texture():
    global objects, canvas
    
    # Ensure an object is selected
    selected_name = object_selector.get()
    if not selected_name:
        messagebox.showerror("No Selection", "Please select an object to map the texture onto.")
        return
    
    # Load the texture file
    file_path = filedialog.askopenfilename(
        filetypes=[("PNG Image", "*.png")],
        title="Select Texture"
    )
    if not file_path:
        return  # User canceled the operation

    # Update the object to include texture info
    for obj in objects:
        if obj.name == selected_name:
            obj.texture = plt.imread(file_path)
            break
    
    # Redraw the plot with the texture
    draw_3d_plot(objects, canvas)

def draw_3d_plot(objects, canvas):
    ax.clear()
    selected_color = 'darkcyan'
    default_color = 'cyan'
    a_val = 0.20
    tColors = 'black'
    tColorSelected = 'red'
    selectedaVal = 0.30

    for obj in objects:
        corners = obj.get_corners()
        verts = [
            [corners[0], corners[1], corners[5], corners[4]],
            [corners[7], corners[6], corners[2], corners[3]],
            [corners[0], corners[3], corners[7], corners[4]],
            [corners[1], corners[2], corners[6], corners[5]],
            [corners[0], corners[1], corners[2], corners[3]],
            [corners[4], corners[5], corners[6], corners[7]],
        ]
        color = selected_color if obj.selected else default_color
        tColor = tColors if obj.selected else tColorSelected
        tColor = tColorSelected if obj.selected else tColors

        a_val = selectedaVal if obj.selected else a_val

        # Check if a texture is applied
        if obj.texture is not None:
            ax.add_collection3d(Poly3DCollection(verts, facecolors=obj.texture, linewidths=1, edgecolors='r', alpha=a_val))
        else:
            ax.add_collection3d(Poly3DCollection(verts, facecolors=color, linewidths=1, edgecolors='r', alpha=a_val))

        center = obj.position + obj.dimensions / 1.5
        ax.text(*center, obj.name, color=tColor)

    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')

    # Calculates axis limitations
    all_positions = np.array([obj.position for obj in objects])
    all_dimensions = np.array([obj.dimensions for obj in objects])
    min_pos = np.min(all_positions, axis=0)
    max_pos = np.max(all_positions + all_dimensions, axis=0)

    ax.set_xlim(min_pos[0], max_pos[0])
    ax.set_ylim(min_pos[1], max_pos[1])
    ax.set_zlim(min_pos[2], max_pos[2])

    # Maintain the aspect ratio of original model
    max_range = np.array([max_pos[0] - min_pos[0], max_pos[1] - min_pos[1], max_pos[2] - min_pos[2]])
    max_range = max(max_range)
    mid_point = (min_pos + max_pos) / 2
    ax.set_xlim(mid_point[0] - max_range / 2, mid_point[0] + max_range / 2)
    ax.set_ylim(mid_point[1] - max_range / 2, mid_point[1] + max_range / 2)
    ax.set_zlim(mid_point[2] - max_range / 2, mid_point[2] + max_range / 2)

    canvas.draw()

def zoom(event):
    global ax, canvas

    zoom_factor = 1.05
    if event.delta > 0:
        zoom_factor = 1 / zoom_factor
    elif event.delta < 0:
        zoom_factor = zoom_factor

    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    zlim = ax.get_zlim()

    x_center = (xlim[0] + xlim[1]) / 2
    y_center = (ylim[0] + ylim[1]) / 2
    z_center = (zlim[0] + zlim[1]) / 2

    x_range = (xlim[1] - xlim[0]) / 2 * zoom_factor
    y_range = (ylim[1] - ylim[0]) / 2 * zoom_factor
    z_range = (zlim[1] - zlim[0]) / 2 * zoom_factor

    ax.set_xlim([x_center - x_range, x_center + x_range])
    ax.set_ylim([y_center - y_range, y_center + y_range])
    ax.set_zlim([z_center - z_range, z_center + z_range])

    canvas.draw()


def on_model_selected(event):
    global current_model_file, objects, model_selector

    selected_file = model_selector.get()
    current_model_file = os.path.join(os.getcwd(), 'data', selected_file)

    objects = read_objects_from_file(current_model_file)

    object_selector.config(values=[obj.name for obj in objects])
    object_selector.set('')

    draw_3d_plot(objects, canvas)


def update_object_data():
    selected_name = object_selector.get()
    obj = next((o for o in objects if o.name == selected_name), None)
    if obj:
        try:
            new_position = [int(float(pos_entry_x.get())), float(pos_entry_y.get()), float(pos_entry_z.get())]
            new_dimensions = [int(float(dim_entry_x.get())), float(dim_entry_y.get()), float(dim_entry_z.get())]

            obj.position = np.array(new_position)
            obj.dimensions = np.array(new_dimensions)
            draw_3d_plot(objects, canvas)
            save_objects(objects, current_model_file)
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter valid Integer Numbers for position and dimensions.\nFloat Values are not Allowed.")

def on_object_selected(event):
    selected_name = object_selector.get()
    for obj in objects:
        obj.selected = (obj.name == selected_name)

    draw_3d_plot(objects, canvas)

    obj = next((o for o in objects if o.name == selected_name), None)
    if obj:
        pos_entry_x.delete(0, tk.END)
        pos_entry_x.insert(0, str(obj.position[0]))
        pos_entry_y.delete(0, tk.END)
        pos_entry_y.insert(0, str(obj.position[1]))
        pos_entry_z.delete(0, tk.END)
        pos_entry_z.insert(0, str(obj.position[2]))

        dim_entry_x.delete(0, tk.END)
        dim_entry_x.insert(0, str(obj.dimensions[0]))
        dim_entry_y.delete(0, tk.END)
        dim_entry_y.insert(0, str(obj.dimensions[1]))
        dim_entry_z.delete(0, tk.END)
        dim_entry_z.insert(0, str(obj.dimensions[2]))

def save_objects(objects, filename="modified_data.txt"):
    with open(filename, "w") as file:
        for obj in objects:
            file.write(f"{obj.name}\n")
            file.write(f"{', '.join(map(str, obj.position))}\n")
            file.write(f"{', '.join(map(str, obj.dimensions))}\n\n")

def read_objects_from_file(filename):
    objects0 = []
    with open(filename, 'r') as file:
        lines = file.readlines()

    i = 0
    while i < len(lines):
        name = lines[i].strip()
        position = list(map(float, lines[i + 1].strip().split(',')))
        dimensions = list(map(float, lines[i + 2].strip().split(',')))
        objects0.append(Object3D(name, position, dimensions))
        i += 4

    return objects0

def list_model_files(directory):
    return [f for f in os.listdir(directory) if f.endswith('.txt') and 'geometry' in f]

def update_model_selector():
    global current_model_file
    """Update the model selector dropdown with the latest model files."""
    global model_selector
    model_directory = os.path.join(os.getcwd(), 'data')
    model_files = list_model_files(model_directory)

    if not model_files:
        model_selector['values'] = []
        messagebox.showerror("No Models Found", "No .txt model files found in the 'data' directory.")
        sys.exit()
    else:
        model_selector['values'] = model_files
        model_selector.set(model_files[0] if model_files else "")

    current_model_file = os.path.join(model_directory, model_files[0])
    draw_3d_plot(objects, canvas)

def open_file():
    global current_model_file, objects

    file_path = filedialog.askopenfilename(
        filetypes=[("Text Model Files", "*.txt")],
        initialdir=os.path.join(os.getcwd(), 'data')
    )
    if file_path:
        current_model_file = file_path
        objects = read_objects_from_file(current_model_file)
        object_selector.config(values=[obj.name for obj in objects])
        object_selector.set('')
        draw_3d_plot(objects, canvas)

def save_file():
    global current_model_file, objects

    if not current_model_file:
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Model Files", "*.txt")],
            initialdir=os.path.join(os.getcwd(), 'data')
        )
        if file_path:
            current_model_file = file_path
    if current_model_file:
        save_objects(objects, current_model_file)

def quit_app():
    root.quit()
    sys.exit(1)

def show_tool_options():
    messagebox.showinfo("Tools", "Tool options not yet implemented.")

def show_app_options():
    messagebox.showinfo("Options", "Application options not yet implemented.")

def export_as_obj():
    global objects
    if not objects:
        messagebox.showerror("Export Error", "No objects to export.")
        return

    obj_file_path = filedialog.asksaveasfilename(
        defaultextension=".obj",
        filetypes=[("OBJ files", "*.obj")],
        initialdir=os.getcwd(),
        title="Save OBJ File"
    )

    if not obj_file_path:
        return

    try:
        with open(obj_file_path, 'w') as file:
            file.write("# Exported OBJ file\n")
            vertex_count = 1

            for obj in objects:
                vertices = obj.get_corners()
                for vertex in vertices:
                    file.write(f"v {vertex[0]} {vertex[1]} {vertex[2]}\n")

                file.write(f"f {vertex_count} {vertex_count+1} {vertex_count+2} {vertex_count+3}\n")
                file.write(f"f {vertex_count+4} {vertex_count+5} {vertex_count+6} {vertex_count+7}\n")
                file.write(f"f {vertex_count} {vertex_count+3} {vertex_count+7} {vertex_count+4}\n")
                file.write(f"f {vertex_count+1} {vertex_count+2} {vertex_count+6} {vertex_count+5}\n")
                file.write(f"f {vertex_count} {vertex_count+1} {vertex_count+5} {vertex_count+4}\n")
                file.write(f"f {vertex_count+2} {vertex_count+3} {vertex_count+7} {vertex_count+6}\n")

                vertex_count += 8

        messagebox.showinfo("Export Success", f"Model exported successfully to {obj_file_path}")

    except Exception as e:
        messagebox.showerror("Export Error", f"Failed to export model: {e}")

def export_as_stl():
    if not objects:
        messagebox.showerror("Export Error", "No objects to export.")
        return

    stl_file_path = filedialog.asksaveasfilename(
        defaultextension=".stl",
        filetypes=[("STL files", "*.stl")],
        initialdir=os.getcwd(),
        title="Save STL File"
    )

    if not stl_file_path:
        return

    try:
        faces = []

        for obj in objects:
            vertices = np.array(obj.get_corners())
            faces.extend([
                [vertices[0], vertices[1], vertices[5]],
                [vertices[5], vertices[4], vertices[0]],
                [vertices[1], vertices[2], vertices[6]],
                [vertices[6], vertices[5], vertices[1]],
                [vertices[2], vertices[3], vertices[7]],
                [vertices[7], vertices[6], vertices[2]],
                [vertices[3], vertices[0], vertices[4]],
                [vertices[4], vertices[7], vertices[3]],
                [vertices[4], vertices[5], vertices[6]],
                [vertices[6], vertices[7], vertices[4]],
                [vertices[0], vertices[1], vertices[2]],
                [vertices[2], vertices[3], vertices[0]],
            ])

        # Create the STL file
        faces = np.array(faces)
        stl_mesh = stl.mesh.Mesh(np.zeros(faces.shape[0], dtype=stl.mesh.Mesh.dtype))
        for i, face in enumerate(faces):
            for j in range(3):
                stl_mesh.vectors[i][j] = face[j]
        stl_mesh.save(stl_file_path)
        messagebox.showinfo("Export Success", f"Model exported successfully to {stl_file_path}")

    except Exception as e:
        messagebox.showerror("Export Error", f"Failed to export model: {e}")

def export_as_text():
    global current_model_file, objects
    if not objects:
        messagebox.showerror("Export Error", "No objects to export.")
        return
    
    if current_model_file:
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Model Files", "*.txt")],
            initialdir=os.getcwd()
        )
        if file_path:
            current_model_file = file_path
        else:
            return
    
    if current_model_file:
        save_objects(objects, current_model_file)

    messagebox.showinfo("Export Success", f"Model exported successfully to {current_model_file}")

def openJsonFile():
    global objects, dim_entry_x, dim_entry_y, dim_entry_z, pos_entry_x, pos_entry_y, pos_entry_z, object_selector
    if messagebox.askyesno("WARNING", "All Current Model Data and Information in Cache will be lost!\nAre you sure you want to Load a JSON Model File?"):
        messagebox.showinfo("Resetting Model Data", "All Model Information is being deleted now.\nThis might take a few seconds...")
        dataFolders = os.listdir(".\\data")
        for file in dataFolders:
            os.remove(f".\\data\\{file}")
        try:
            os.rmdir('.\\data')
            os.remove('.\\hash_database.json')
        except FileNotFoundError:
            pass

        try:
            with open('.\\filename.txt','r') as outf:
                data = outf.readline()
                os.remove(data.replace("\n",''))
                getBaseName = os.path.basename(os.path.dirname(data))
            
        except FileNotFoundError:
            pass
            try:
                os.rmdir(f"{os.path.dirname(__file__)}\\models\\{getBaseName}")
                os.rmdir(f"{os.path.dirname(__file__)}\\models")
            except FileNotFoundError:
                pass
        json2modelBase()
        update_model_selector()

        file_path = os.listdir(".\\data")

        current_model_file = f"{os.path.dirname(__file__)}\\data\\{file_path[0]}"
        objects = read_objects_from_file(current_model_file)
        object_selector.config(values=[obj.name for obj in objects])
        object_selector.set('')
        draw_3d_plot(objects, canvas)

        with open('.\\hash_database.json','w') as f1:
            f1.write("JSON File Loaded, DO NOT CONVERT TO BJSON.")

        
    else:
        messagebox.showinfo("Data Reset Canceled", "Model Data has not been deleted.\nAll settings untouched.")
        return

def openBjsonFile():
    global objects, dim_entry_x, dim_entry_y, dim_entry_z, pos_entry_x, pos_entry_y, pos_entry_z, object_selector
    if messagebox.askyesno("WARNING", "All Current Model Data and Information in Cache will be lost!\nAre you sure you want to Load another BJSON Model File?"):
        messagebox.showinfo("Resetting Model Data", "All Model Information is being deleted now.\nThis might take a few seconds...")
        dataFolders = os.listdir(".\\data")
        for file in dataFolders:
            os.remove(f".\\data\\{file}")
        try:
            os.rmdir('.\\data')
            os.remove('.\\hash_database.json')
        except FileNotFoundError:
            pass

        try:
            with open('.\\filename.txt','r') as outf:
                data = outf.readline()
                os.remove(data.replace("\n",''))
                getBaseName = os.path.basename(os.path.dirname(data))
            
        except FileNotFoundError:
            pass
            try:
                os.rmdir(f"{os.path.dirname(__file__)}\\models\\{getBaseName}")
                os.rmdir(f"{os.path.dirname(__file__)}\\models")
            except FileNotFoundError:
                pass

        bjson2models()
        update_model_selector()

        file_path = os.listdir(".\\data")

        current_model_file = f"{os.path.dirname(__file__)}\\data\\{file_path[0]}"
        objects = read_objects_from_file(current_model_file)
        object_selector.config(values=[obj.name for obj in objects])
        object_selector.set('')
        draw_3d_plot(objects, canvas)

        
    else:
        messagebox.showinfo("Data Reset Canceled", "Model Data has not been deleted.\nAll settings untouched.")
        return

def scale_model(factor):
    global objects, dim_entry_x, dim_entry_y, dim_entry_z, pos_entry_x, pos_entry_y, pos_entry_z, object_selector

    for obj in objects:
        original_position = obj.position.copy()
        
        obj.scale(factor)
        if factor == 2:
            obj.position = [coord / 2 for coord in original_position]
        elif factor == 0.5:
            obj.position = [coord * 2 for coord in original_position]
    
    draw_3d_plot(objects, canvas)

    selected_name = object_selector.get()
    if selected_name:
        obj = next((o for o in objects if o.name == selected_name), None)
        if obj:
            dim_entry_x.delete(0, tk.END)
            dim_entry_x.insert(0, str(obj.dimensions[0]))
            dim_entry_y.delete(0, tk.END)
            dim_entry_y.insert(0, str(obj.dimensions[1]))
            dim_entry_z.delete(0, tk.END)
            dim_entry_z.insert(0, str(obj.dimensions[2]))
            
            pos_entry_x.delete(0, tk.END)
            pos_entry_x.insert(0, str(obj.position[0]))
            pos_entry_y.delete(0, tk.END)
            pos_entry_y.insert(0, str(obj.position[1]))
            pos_entry_z.delete(0, tk.END)
            pos_entry_z.insert(0, str(obj.position[2]))

def models2jsonf(answer='--json'):
    with open(".\\filename.txt",'r') as f0:
        geoPath = f0.readline()
        geoPath = geoPath.replace("\n",'')

    with open(geoPath, "r") as f:
        data = json.load(f)

    directory = ".\\data"
    text_files = [f for f in os.listdir(directory) if f.startswith("geometry.") and f.endswith(".txt")]

    def get_base_name_and_number(name):
        match = re.match(r"(\D+)(\d*)", name)
        base_name = match.group(1)
        number = int(match.group(2)) if match.group(2) else 0
        return base_name, number

    for text_file in text_files:
        model_name = text_file[len("geometry."):-len(".txt")]

        with open(os.path.join(directory, text_file), "r") as f:
            lines = f.read().strip().splitlines()

        parsed_data = {}
        current_name = None
        for line in lines:
            line = line.strip()

            if not line:
                continue

            if re.match(r"^\w+\d*$", line):
                current_name = line
                parsed_data[current_name] = {}
            elif current_name and "origin" not in parsed_data[current_name]:
                try:
                    parsed_data[current_name]["origin"] = list(map(float, line.split(", ")))
                except ValueError:
                    print(f"Skipping invalid origin line: {line}")
            elif current_name:
                try:
                    parsed_data[current_name]["size"] = list(map(float, line.split(", ")))
                except ValueError:
                    print(f"Skipping invalid size line: {line}")

        grouped_data = {}
        for key in parsed_data:
            base_name, number = get_base_name_and_number(key)
            if base_name not in grouped_data:
                grouped_data[base_name] = []
            grouped_data[base_name].append((number, parsed_data[key]))

        for base_name in grouped_data:
            grouped_data[base_name].sort(key=lambda x: x[0])

        if f"geometry.{model_name}" in data:
            for bone in data[f"geometry.{model_name}"]["bones"]:
                name = bone["name"]
                if name in grouped_data:
                    for i, (number, update_data) in enumerate(grouped_data[name]):
                        if i < len(bone["cubes"]):
                            bone["cubes"][i]["origin"] = update_data.get("origin", bone["cubes"][i]["origin"])
                            bone["cubes"][i]["size"] = update_data.get("size", bone["cubes"][i]["size"])

    with open(f"{os.path.dirname(geoPath)}\\geometry_updated.json", "w") as f:
        json.dump(data, f, indent=4)

    print(f"Updated data saved in {geoPath}")

    time.sleep(0.5)
    filename0 = os.path.basename(geoPath)

    getbasename = os.path.basename(os.path.dirname(geoPath))

    if answer == "--bjson":
        if os.path.exists(".\\hash_database.json"):
            with open(".\\hash_database.json", 'r') as f01:
                if "JSON File Loaded, DO NOT CONVERT TO BJSON." not in f01.read():
                    bjson.convertJsonToBjson(f"{os.path.dirname(geoPath)}\\geometry_updated.json")
                else:
                    messagebox.showerror("Error","BJSON Model Editor ran into an Issue.\nAnd is unable to Process your Current Conversion Request.\n\nJSON Files cannot be converted into BJSON without proper BJSON Hash Keys.\n\nThese are obtained through Legit BJSON Model Files.")
                    return

        messagebox.showinfo("Success!", f"BJSON Model File Saved at: {os.path.dirname(__file__)}\\{filename0.replace('.json','.bjson')}")
    elif answer == "--json":
        messagebox.showinfo("Success!", f"JSON Model File Saved at: {geoPath}")
        pass
    else:
        messagebox.showerror("Error","BJSON Model Editor ran into an Issue, and is unable to Process your Current Conversion Request.")
        return

def json2bjsonFiles():
    jsonFile = bjson.convertJsonToBjson

def json2model(main_string, directory_name, random_string, bjsonFile, directory=os.path.dirname(__file__)):
    if '"size": [' not in main_string:
        messagebox.showerror('Error',"The Provided JSON/BJSON File was Not a Model.")
        sys.exit(1)
    else:
        json_path = f'{directory}\\models\\{directory_name}\\{random_string}.json'
        with open(json_path, 'w') as json_file:
            json_file.write(main_string)

        with open(json_path, "r") as new_json_file:
            json_data = json.load(new_json_file)

        for key, value in json_data.items():
            if key.startswith("geometry.") and "bones" in value:
                bones = value["bones"]
                output_lines = []
                for bone in bones:
                    if "name" in bone and "cubes" in bone:
                        name = bone["name"]
                        cubes = bone["cubes"]
                        for cube in cubes:
                            if "origin" in cube and "size" in cube:
                                origin = cube["origin"]
                                size = cube["size"]
                                output_lines.append(f"{name}")
                                output_lines.append(f"{origin[0]}, {origin[1]}, {origin[2]}")
                                output_lines.append(f"{size[0]}, {size[1]}, {size[2]}")
                                output_lines.append("")

                output_directory = os.path.join(directory, "data")
                os.makedirs(output_directory, exist_ok=True)
                output_path = os.path.join(output_directory, f"{key}.txt")
                with open(output_path, 'w') as output_file:
                    output_file.write("\n".join(output_lines))

        print(f"Converted BJSON Data Saved: {output_directory}")
        with open(f'{directory}\\filename.txt','w') as outf:
            outf.write(f'{directory}\\models\\{directory_name}\\{random_string}.json\n')
            outf.write(f"{bjsonFile}")

    time.sleep(0.5)
    for filename in os.listdir(f"{directory}\\data"):
        if filename.endswith(".txt") and "geometry" in filename:
            file_path = os.path.join(f"{directory}\\data", filename)
        
            head_counter = 0
            body_counter = 0
        
            with open(file_path, 'r') as file:
                lines = file.readlines()
        
            new_lines = []
            for line in lines:
                if "head" in line:
                    new_line = re.sub(r'\bhead\b', f'head{head_counter}', line)
                    head_counter += 1
                elif "body" in line:
                    new_line = re.sub(r'\bbody\b', f'body{body_counter}', line)
                    body_counter += 1
                else:
                    new_line = line
            
                new_lines.append(new_line)

            with open(file_path, 'w') as file:
                file.writelines(new_lines)

def bjson2models():
    if not os.path.exists('.\\filename.txt'):
        messagebox.showinfo("Welcome", f"Welcome to the MC3DS BJSON Model Editor!\nYou can now edit MC3DS Models easier than ever.\n\nVersion: v{VERSION}.0\nDeveloped by: Cracko298.")
    
    character = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(character) for _ in range(16))
    directory = os.path.dirname(__file__)
    bjsonFile = filedialog.askopenfilename(initialdir=f"{os.path.dirname(__file__)}", filetypes=[("BJSON Model Files", "*.bjson")])

    if not bjsonFile:
        bjsonFile = f"{os.path.dirname(__file__)}\\modules\\exampleModel.bjson"

    file_name0 = os.path.basename(bjsonFile)
    directory_name = file_name0.replace('.bjson','')
    os.makedirs(f"{directory}\\models\\{directory_name}",exist_ok=True)

    main_string = bjson.convertBjsonToJson(bjsonFile)

    json2model(main_string, directory_name, random_string, bjsonFile, directory)

def json2modelBase():
    character = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(character) for _ in range(16))
    directory = os.path.dirname(__file__)
    jsonFile = filedialog.askopenfilename(initialdir=f"{os.path.dirname(__file__)}", filetypes=[("JSON Model Files", "*.json")])
    
    if not jsonFile:
        messagebox.showerror("Error", "No JSON Model File Selected.")
        return
    
    file_name0 = os.path.basename(jsonFile)
    directory_name = file_name0.replace('.json','')
    os.makedirs(f"{directory}\\models\\{directory_name}",exist_ok=True)

    with open(jsonFile,'r') as f0:
        main_string = f0.read()

    json2model(main_string, directory_name, random_string, jsonFile, directory)

def savetojson():
    models2jsonf('--json')

def savetobjson():
    models2jsonf('--bjson')

def updateApplication():
    global VERSION
    api_url = "https://api.github.com/repos/Cracko298/MC3DS-3D-Model-Editor/releases/latest"
    response = requests.get(api_url)
    response_data = response.json()
    latest_version_tag = response_data['tag_name']
    try:
        latest_version = float(latest_version_tag)
    except ValueError:
        print("Error: Latest version tag could not be converted to a float.")
        messagebox.showerror("Error", "Newest Version of BJSON Model Editor isn't a float value.")
        return

    if latest_version > VERSION:
        answer = messagebox.askyesno("Update Avaliable", "An Update is Avaliable to Download.\nWould you like to download and install it?\n\nThis will require an Application restart automatically after installing.\nAll unsaved Model Data will be lost.\nAll saved Model Data won't be touched.")

        if answer:
            root.destroy()
            assets = response_data['assets']
            zip_url = None
            for asset in assets:
                if asset['name'].endswith('.zip'):
                    zip_url = asset['browser_download_url']
                    break

            if zip_url is None:
                print("Error: No ZIP file found in the latest release.")
                messagebox.showerror("Error", "No ZIP file found in the latest release.")
                return
            
            zip_response = requests.get(zip_url)
            zip_data = zip_response.content

            with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
                extract_path = os.path.dirname(os.path.abspath(__file__))
                z.extractall(extract_path)

            os.system(f'python {__file__}')

    if latest_version <= VERSION:
        answer = messagebox.showinfo("Notice", "You have the Latest Release of MC3DS BJSON Model Editor.")
        return

def basicAboutDiag():
    messagebox.showinfo("AboutDiag", f"Version: '{VERSION}'.\nHash Database Exists?: '{os.path.exists(".\\hash_database.json")}'.\nModel Cache File Exists?: '{os.path.exists(".\\filename.txt")}'.\n\nMC3DS BJSON Model Editor Developer: Cracko298.\npyBjson Python Module Developer: STBrian.")

def contactsDiag():
    messagebox.showinfo("AboutDiag", f"Personal Email: rfddfd5567@gmail.com\nBuisness Email: batchbatch298@outlook.com\n\nName: Phinehas Charles Beresford (Cracko298).")

def licsenseDiag():
    messagebox.showinfo("AboutDiag", f"Current License: 'Apache License v2.0'.\n\nPlease read the License throughly before 3rd party distrobution.")

def main():
    global root, ax, canvas, objects, object_selector, pos_entry_x, pos_entry_y, pos_entry_z, dim_entry_x, dim_entry_y, dim_entry_z, model_selector
    global current_model_file

    root = tk.Tk()
    root.title("BJSON Model Editor")
    root.protocol("WM_DELETE_WINDOW", quit_app)
    if os.path.exists('.\\data') == False:
        bjson2models()

    menu_bar = tk.Menu(root)
    root.config(menu=menu_bar)

    file_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="File", menu=file_menu)

    open_menu = tk.Menu(file_menu, tearoff=0)
    file_menu.add_cascade(label="Open", menu=open_menu)
    open_menu.add_command(label="Open Text Model", command=open_file)
    open_menu.add_command(label="Open BJSON Model", command=openBjsonFile)
    open_menu.add_command(label="Open JSON Model", command=openJsonFile)

    save_menu = tk.Menu(file_menu, tearoff=0)
    file_menu.add_cascade(label="Save", menu=save_menu)
    save_menu.add_command(label="Save Text File", command=save_file)
    save_menu.add_command(label="Save Text File As", command=export_as_text)
    save_menu.add_command(label="Save To JSON", command=savetojson)
    save_menu.add_command(label="Save To BJSON", command=savetobjson)

    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=quit_app)

    # Tools menu
    tools_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Tools", menu=tools_menu)
    scaling_menu = tk.Menu(tools_menu, tearoff=0)

    export_menu = tk.Menu(tools_menu, tearoff=0)
    export_menu.add_command(label="Export as OBJ", command=export_as_obj)
    export_menu.add_command(label="Export as STL", command=export_as_stl)
    export_menu.add_command(label="Export as Text", command=export_as_text)
    tools_menu.add_cascade(label="Export as Model", menu=export_menu)

    tools_menu.add_cascade(label="Scaling", menu=scaling_menu)
    scaling_menu.add_command(label="Scale Up (2.0x)", command=lambda: scale_model(2))
    scaling_menu.add_command(label="Scale Down (0.5x)", command=lambda: scale_model(0.5))
    tools_menu.add_separator()
    tools_menu.add_command(label="Map Texture", command=map_texture)


    # Options menu
    options_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Options", menu=options_menu)
    options_menu.add_command(label="Update Application", command=updateApplication)

    about_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="About", menu=about_menu)
    about_menu.add_command(label="About", command=basicAboutDiag)
    about_menu.add_command(label="Contact", command=contactsDiag)
    about_menu.add_command(label="License", command=licsenseDiag)

    # List model files
    model_directory = os.path.join(os.getcwd(), 'data')
    model_files = list_model_files(model_directory)

    if not model_files:
        messagebox.showerror("No Models Found", "No .txt model files found in the 'data' directory.")
        sys.exit()

    current_model_file = os.path.join(model_directory, model_files[0])

    # Load objects from the default model file
    objects = read_objects_from_file(current_model_file)

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    canvas.get_tk_widget().bind_all("<MouseWheel>", zoom)
    draw_3d_plot(objects, canvas)

    # Setting up the control panel
    control_panel = tk.Frame(root)
    control_panel.pack(side=tk.RIGHT, fill=tk.Y)

    # Model selector
    model_selector_label = tk.Label(control_panel, text="Select Model:")
    model_selector_label.pack(pady=5)

    model_selector = ttk.Combobox(control_panel, values=model_files)
    model_selector.pack(pady=5, padx=10)
    model_selector.bind("<<ComboboxSelected>>", on_model_selected)

    # Object selector
    object_selector_label = tk.Label(control_panel, text="Select Object:")
    object_selector_label.pack(pady=5)

    object_selector = ttk.Combobox(control_panel)
    object_selector.pack(pady=5)
    object_selector.bind("<<ComboboxSelected>>", on_object_selected)

    pos_label = tk.Label(control_panel, text="Position (x, y, z):")
    pos_label.pack(pady=5)

    pos_frame = tk.Frame(control_panel)
    pos_frame.pack(pady=5)
    pos_entry_x = tk.Entry(pos_frame, width=5)
    pos_entry_x.pack(side=tk.LEFT)
    pos_entry_y = tk.Entry(pos_frame, width=5)
    pos_entry_y.pack(side=tk.LEFT)
    pos_entry_z = tk.Entry(pos_frame, width=5)
    pos_entry_z.pack(side=tk.LEFT)

    dim_label = tk.Label(control_panel, text="Dimensions (dx, dy, dz):")
    dim_label.pack(pady=5)

    dim_frame = tk.Frame(control_panel)
    dim_frame.pack(pady=5)
    dim_entry_x = tk.Entry(dim_frame, width=5)
    dim_entry_x.pack(side=tk.LEFT)
    dim_entry_y = tk.Entry(dim_frame, width=5)
    dim_entry_y.pack(side=tk.LEFT)
    dim_entry_z = tk.Entry(dim_frame, width=5)
    dim_entry_z.pack(side=tk.LEFT)

    update_button = tk.Button(control_panel, text="Update Object", command=update_object_data)
    update_button.pack(pady=10)

    model_selector.config(width=20)
    object_selector.config(width=15)

    root.mainloop()

if __name__ == "__main__":
    main()
