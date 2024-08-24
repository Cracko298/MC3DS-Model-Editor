import sys, shutil, os, random, string, json, re, time, zipfile, io, base64, struct, subprocess, importlib
from tkinter import ttk, messagebox, filedialog, simpledialog
import tkinter as tk
VERSION = 0.5
yxFloatValue = 0.3
zoom_factor = 0
inZoomFactor = 0.9
outZoomFactor = 1.1
azimuth = 30
elevation = 30
increaseEandA = 5

try:
    import stl, requests, lxml, lxml.etree
    import numpy as np
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from modules import bjson, conversions, JOAAThash, updateDatabase
    from pygltflib import GLTF2, Scene, Node, Mesh, Primitive, Buffer, BufferView, Accessor, Asset

except ImportError:
    answ = messagebox.askyesno("Notice", "The script needs to install some dependancies in order to run correctly.\nMay it install dependancies from 'requirements.txt'?")
    if answ:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        messagebox.showinfo("Notice","The script has installed some python Modules.\nIt will now restart.")
        time.sleep(1)
        os.system(f'python "{__file__}"')
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
    
    selected_name = object_selector.get()
    if not selected_name:
        messagebox.showerror("No Selection", "Please select an object to map the texture onto.")
        return
    
    file_path = filedialog.askopenfilename(
        filetypes=[("PNG Image", "*.png")],
        title="Select Texture"
    )
    if not file_path:
        return

    for obj in objects:
        if obj.name == selected_name:
            obj.texture = plt.imread(file_path)
            break
    
    draw_3d_plot(objects, canvas)

def draw_3d_plot(objects, canvas):
    global azimuth, elevation
    ax.clear()
    ax.set_facecolor('darkgray')
    ax.view_init(elevation, azimuth)
    selected_color = 'darkcyan'
    default_color = 'cyan'
    b_Val = 0.15
    tColors = 'black'
    tColorSelected = 'red'
    selectedaVal = 0.30
    light_red = (1, 0.5, 0.5, 0.8)

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

        a_val = selectedaVal if obj.selected else b_Val

        # Check if a texture is applied
        if obj.texture is not None:
            ax.add_collection3d(Poly3DCollection(verts, facecolors=obj.texture, linewidths=1, edgecolors=light_red, alpha=a_val))
        else:
            ax.add_collection3d(Poly3DCollection(verts, facecolors=color, linewidths=1, edgecolors=light_red, alpha=a_val))

        center = obj.position + obj.dimensions / 1.5
        if obj.selected:
            ax.text(*center+7, obj.name, color=tColor, fontsize=8, fontweight='bold', bbox=dict(alpha=0.7))
        else:
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
    global ax, canvas, current_model_file, zoom_factor

    if event.delta > 0:
        zoom_factor = inZoomFactor
    elif event.delta < 0:
        zoom_factor = outZoomFactor

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
            new_position = [float(pos_entry_x.get()), float(pos_entry_y.get()), float(pos_entry_z.get())]
            new_dimensions = [float(dim_entry_x.get()), float(dim_entry_y.get()), float(dim_entry_z.get())]

            obj.position = np.array(new_position)
            obj.dimensions = np.array(new_dimensions)
            draw_3d_plot(objects, canvas)
            save_objects(objects, current_model_file)
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter valid Ineger/Floating Point Numbers\nUsage for positions and dimensions.\n\nStrings (Non Numerical Numbers) are not Allowed.")
            return

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
        # This regex will match a number at the front and then the rest of the name
        match = re.match(r"(\d*)(\D+)", name)
        if match:
            number = int(match.group(1)) if match.group(1) else 0
            base_name = match.group(2)
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

                else:
            # Handle cases where the name is unique and should not be iterated
                   if name in parsed_data:
                        bone["cubes"][0]["origin"] = parsed_data[name].get("origin", bone["cubes"][0]["origin"])
                        bone["cubes"][0]["size"] = parsed_data[name].get("size", bone["cubes"][0]["size"])



    with open(f"{os.path.dirname(geoPath)}\\geometry_updated.json", "w") as f:
        json.dump(data, f, indent=4)

    print(f"Updated data saved in {geoPath}")

    def convert_floats_to_ints(data):
        if isinstance(data, dict):
            return {key: convert_floats_to_ints(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [convert_floats_to_ints(item) for item in data]
        elif isinstance(data, float):
            if data.is_integer():
                return int(data)
            else:
                return data
        else:
            return data

    def process_json_file(filename):
        with open(filename, 'r') as file:
            data = json.load(file)

        modified_data = convert_floats_to_ints(data)

        with open(filename, 'w') as file:
            json.dump(modified_data, file, indent=4)

    process_json_file(f"{os.path.dirname(geoPath)}\\geometry_updated.json")
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

def bodyAndHeadItterations(mode=0):
    global current_model_file
    directory = os.path.dirname(__file__)
    if mode == 1:
        file_path = f"{current_model_file}"
        head_counter = 0
        body_counter = 0
        headOcc = 0
        bodyOcc = 0
        
        with open(file_path, 'r') as file:
            lines = file.readlines()
            file.seek(0x00)
            whole_file = file.read()
            file.seek(0x00)
            headOcc += whole_file.count("head")
            file.seek(0x00)
            bodyOcc += whole_file.count("body")
            print(headOcc, bodyOcc)
        
        new_lines = []
        for line in lines:
            if "head" in line and headOcc > 1:
                new_line = re.sub(r'\bhead\b', f'{head_counter}head', line)
                head_counter += 1
            elif "body" in line and bodyOcc > 1:
                new_line = re.sub(r'\bbody\b', f'{body_counter}body', line)
                body_counter += 1
            else:
                new_line = line
        
            new_lines.append(new_line)

        with open(file_path, 'w') as file:
            file.writelines(new_lines)

        return
    else:
        for filename in os.listdir(f"{directory}\\data"):
            if filename.endswith(".txt") and "geometry." in filename:
                file_path = os.path.join(f"{directory}\\data", filename)
        
                head_counter = 0
                body_counter = 0
                headOcc = 0
                bodyOcc = 0
        
                with open(file_path, 'r') as file:
                    lines = file.readlines()
                    file.seek(0x00)
                    whole_file = file.read()
                    headOcc += whole_file.count("head")
                    bodyOcc += whole_file.count("body")
                    print(headOcc, bodyOcc)
        
                new_lines = []
                for line in lines:
                    if "head" in line and headOcc > 1:
                        new_line = re.sub(r'\bhead\b', f'{head_counter}head', line)
                        head_counter += 1
                    elif "body" in line and bodyOcc > 1:
                        new_line = re.sub(r'\bbody\b', f'{body_counter}body', line)
                        body_counter += 1
                    else:
                        new_line = line
            
                    new_lines.append(new_line)

                with open(file_path, 'w') as file:
                    file.writelines(new_lines)

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
    bodyAndHeadItterations()

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

def export_as_gltf():
    global objects, current_model_file
    if not objects:
        messagebox.showerror("Export Error", "No objects to export.")
        return

    gltf_file_path = filedialog.asksaveasfilename(
        defaultextension=".gltf",
        filetypes=[("GLTF files", "*.gltf")],
        initialdir=os.getcwd(),
        title="Save GLTF File"
    )

    if not gltf_file_path:
        return

    with open(current_model_file, 'r') as file:
        data = file.read()

    parts = data.strip().split("\n\n")
    vertices = []
    indices = []
    index_offset = 0

    for part in parts:
        lines = part.split("\n")
        if len(lines) < 3:
            continue
        position = list(map(float, lines[1].split(", ")))
        size = list(map(float, lines[2].split(", ")))
        x, y, z = position
        w, h, d = size
        vertices.extend([
            x, y, z,
            x + w, y, z,
            x + w, y + h, z,
            x, y + h, z,
            x, y, z + d,
            x + w, y, z + d,
            x + w, y + h, z + d,
            x, y + h, z + d
        ])

        indices.extend([
            index_offset, index_offset + 2, index_offset + 1, index_offset, index_offset + 3, index_offset + 2,
            index_offset + 4, index_offset + 5, index_offset + 6, index_offset + 4, index_offset + 6, index_offset + 7,
            index_offset, index_offset + 4, index_offset + 7, index_offset, index_offset + 7, index_offset + 3,
            index_offset + 1, index_offset + 2, index_offset + 6, index_offset + 1, index_offset + 6, index_offset + 5,
            index_offset + 2, index_offset + 3, index_offset + 7, index_offset + 2, index_offset + 7, index_offset + 6,
            index_offset, index_offset + 1, index_offset + 5, index_offset, index_offset + 5, index_offset + 4
        ])
        index_offset += 8

    gltf = GLTF2()
    scene = Scene()
    gltf.scenes.append(scene)
    gltf.scene = 0
    node = Node()
    gltf.nodes.append(node)
    scene.nodes.append(0)
    mesh = Mesh()
    primitive = Primitive()
    mesh.primitives.append(primitive)
    gltf.meshes.append(mesh)
    node.mesh = 0

    vertices_bytes = struct.pack(f'{len(vertices)}f', *vertices)
    indices_bytes = struct.pack(f'{len(indices)}I', *indices)

    buffer_data = vertices_bytes + indices_bytes
    buffer = Buffer()
    buffer.uri = "data:application/octet-stream;base64," + base64.b64encode(buffer_data).decode('utf-8')
    buffer.byteLength = len(buffer_data)
    gltf.buffers.append(buffer)
    bufferView_vertices = BufferView()
    bufferView_vertices.buffer = 0
    bufferView_vertices.byteOffset = 0
    bufferView_vertices.byteLength = len(vertices_bytes)
    gltf.bufferViews.append(bufferView_vertices)
    bufferView_indices = BufferView()
    bufferView_indices.buffer = 0
    bufferView_indices.byteOffset = len(vertices_bytes)
    bufferView_indices.byteLength = len(indices_bytes)
    gltf.bufferViews.append(bufferView_indices)
    accessor_vertices = Accessor()
    accessor_vertices.bufferView = 0
    accessor_vertices.byteOffset = 0
    accessor_vertices.componentType = 5126
    accessor_vertices.count = len(vertices) // 3
    accessor_vertices.type = "VEC3"
    gltf.accessors.append(accessor_vertices)
    accessor_indices = Accessor()
    accessor_indices.bufferView = 1
    accessor_indices.byteOffset = 0
    accessor_indices.componentType = 5125
    accessor_indices.count = len(indices)
    accessor_indices.type = "SCALAR"
    gltf.accessors.append(accessor_indices)
    primitive.attributes.POSITION = 0
    primitive.indices = 1
    gltf.save(gltf_file_path)

def parse_input_file(filename):
    with open(filename, 'r') as file:
        lines = [line.strip() for line in file.readlines() if line.strip()]

    data = []
    for i in range(0, len(lines), 3):
        name = lines[i].strip()
        position = tuple(map(int, lines[i + 1].strip().split(', ')))
        size = tuple(map(int, lines[i + 2].strip().split(', ')))
        data.append((name, position, size))
    
    return data

def export_as_ply():
    global objects, current_model_file
    data = parse_input_file(current_model_file)
    if not objects:
        messagebox.showerror("Export Error", "No objects to export.")
        return

    ply_file_path = filedialog.asksaveasfilename(
        defaultextension=".ply",
        filetypes=[("PLY files", "*.ply")],
        initialdir=os.getcwd(),
        title="Save PLY File"
    )

    if not ply_file_path:
        return
    
    with open(ply_file_path, 'w') as file:
        vertex_list = []
        face_list = []
        
        for name, position, size in data:
            x, y, z = position
            w, h, d = size
            
            # Vertices
            vertices = [
                (x, y, z), (x + w, y, z), (x + w, y + h, z), (x, y + h, z),
                (x, y, z + d), (x + w, y, z + d), (x + w, y + h, z + d), (x, y + h, z + d)
            ]
            vertex_list.extend(vertices)
            
            # Faces (indices)
            start_index = len(vertex_list) - 8
            faces = [
                (start_index, start_index + 1, start_index + 2, start_index + 3),
                (start_index + 4, start_index + 5, start_index + 6, start_index + 7),
                (start_index, start_index + 1, start_index + 5, start_index + 4),
                (start_index + 1, start_index + 2, start_index + 6, start_index + 5),
                (start_index + 2, start_index + 3, start_index + 7, start_index + 6),
                (start_index + 3, start_index + 0, start_index + 4, start_index + 7)
            ]
            face_list.extend(faces)
        
        # Write header
        file.write("ply\n")
        file.write("format ascii 1.0\n")
        file.write(f"element vertex {len(vertex_list)}\n")
        file.write("property float x\n")
        file.write("property float y\n")
        file.write("property float z\n")
        file.write(f"element face {len(face_list)}\n")
        file.write("property list uchar int vertex_indices\n")
        file.write("end_header\n")
        
        # Write vertices
        for vertex in vertex_list:
            file.write(f"{vertex[0]} {vertex[1]} {vertex[2]}\n")
        
        # Write faces
        for face in face_list:
            file.write(f"4 {face[0]} {face[1]} {face[2]} {face[3]}\n")

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
                if asset['name'].endswith('.zip') and ".py" in os.path.basename(__file__):
                    zip_url = asset['browser_download_url']
                    break
                if asset['name'].endswith('.exe') and ".exe" in os.path.basename(__file__):
                    exe_url = asset['browser_download_url']
                    break

            if zip_url is None:
                print("Error: No ZIP file found in the latest release.")
                messagebox.showerror("Error", "No ZIP file found in the latest release.")
                return
            
            if ".py" in os.path.basename(__file__):
                zip_response = requests.get(zip_url)
                zip_data = zip_response.content

                with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
                    extract_path = os.path.dirname(os.path.abspath(__file__))
                    z.extractall(extract_path)

                os.system(f'python {__file__}')
                quit_app()

            else:
                if exe_url is None:
                    print("Error: No Executable file found in the latest release.")
                    messagebox.showerror("Error", "No Executable file found in the latest release.")
                    return
                
                exe_response = requests.get(exe_url)
                exe_data = exe_response.content

                with open(f"{os.path.dirname}\\{os.path.basename(__file__)}", 'w') as f0:
                    f0.write(exe_data)
                    f0.close()
                
                os.system(f"start {__file__}")
                quit_app()

    if latest_version <= VERSION:
        answer = messagebox.showinfo("Notice", "You have the Latest Release of MC3DS BJSON Model Editor.")
        return

def basicAboutDiag():
    messagebox.showinfo("AboutDiag", f"Version: '{VERSION}'.\nHash Database Exists?: '{os.path.exists(".\\hash_database.json")}'.\nModel Cache File Exists?: '{os.path.exists(".\\filename.txt")}'.\n\nMC3DS BJSON Model Editor Developer: Cracko298.\npyBjson Python Module Developer: STBrian.")

def contactsDiag():
    messagebox.showinfo("AboutDiag", f"Personal Email: rfddfd5567@gmail.com\nBuisness Email: batchbatch298@outlook.com\n\nName: Phinehas Charles Beresford (Cracko298).")

def licsenseDiag():
    messagebox.showinfo("AboutDiag", f"Current License: 'Apache License v2.0'.\n\nPlease read the License throughly before 3rd party distrobution.")

def export_as_dae():
    global objects, current_model_file

    data = parse_input_file(current_model_file)
    if not objects:
        messagebox.showerror("Export Error", "No objects to export.")
        return

    output_file = filedialog.asksaveasfilename(
        defaultextension=".dae",
        filetypes=[("DAE files", "*.dae")],
        initialdir=os.getcwd(),
        title="Save DAE File"
    )

    if not output_file:
        return
    
    COLLADA_NS = "http://www.collada.org/2005/11/COLLADASchema"
    ET = lxml.etree.ElementTree
    root = lxml.etree.Element("COLLADA", xmlns=COLLADA_NS, version="1.4.1")

    asset = lxml.etree.SubElement(root, "asset")
    lxml.etree.SubElement(asset, "contributor")
    lxml.etree.SubElement(asset, "created").text = "2024-08-18T00:00:00"
    lxml.etree.SubElement(asset, "modified").text = "2024-08-18T00:00:00"
    lxml.etree.SubElement(asset, "unit", name="meter", meter="1.0")
    lxml.etree.SubElement(asset, "up_axis").text = "Y_UP"

    library_geometries = lxml.etree.SubElement(root, "library_geometries")

    for name, position, size in data:
        geometry = lxml.etree.SubElement(library_geometries, "geometry", id=name, name=name)
        mesh = lxml.etree.SubElement(geometry, "mesh")

        x, y, z = position
        w, h, d = size
        vertices = [
            (x, y, z), (x + w, y, z), (x + w, y + h, z), (x, y + h, z),
            (x, y, z + d), (x + w, y, z + d), (x + w, y + h, z + d), (x, y + h, z + d)
        ]
        vertex_data = " ".join(f"{v[0]} {v[1]} {v[2]}" for v in vertices)
        
        source = lxml.etree.SubElement(mesh, "source", id=f"{name}_positions")
        float_array = lxml.etree.SubElement(source, "float_array", id=f"{name}_positions-array", count=str(len(vertices) * 3))
        float_array.text = vertex_data
        
        technique_common = lxml.etree.SubElement(source, "technique_common")
        accessor = lxml.etree.SubElement(technique_common, "accessor", source=f"#{name}_positions-array", count="8", stride="3")
        lxml.etree.SubElement(accessor, "param", name="X", type="float")
        lxml.etree.SubElement(accessor, "param", name="Y", type="float")
        lxml.etree.SubElement(accessor, "param", name="Z", type="float")

        vertices_elem = lxml.etree.SubElement(mesh, "vertices", id=f"{name}_vertices")
        lxml.etree.SubElement(vertices_elem, "input", semantic="POSITION", source=f"#{name}_positions")

        triangles = lxml.etree.SubElement(mesh, "triangles", count="12")
        lxml.etree.SubElement(triangles, "input", semantic="VERTEX", source=f"#{name}_vertices", offset="0")
        p_elem = lxml.etree.SubElement(triangles, "p")
        faces = [
            (0, 1, 2), (2, 3, 0), (4, 5, 6), (6, 7, 4),
            (0, 1, 5), (5, 4, 0), (1, 2, 6), (6, 5, 1),
            (2, 3, 7), (7, 6, 2), (3, 0, 4), (4, 7, 3)
        ]
        p_elem.text = " ".join(str(index) for face in faces for index in face)

    tree = ET(root)
    tree.write(output_file, pretty_print=True, xml_declaration=True, encoding='UTF-8')

def data2json():
    global objects, current_model_file

    modelFile = os.path.basename(current_model_file)
    modelFile = modelFile.replace('.txt','')
    
    with open('.\\filename.txt','r') as f0:
        firstLine = f0.readline()
        firstLine = firstLine.replace("\n","")
        f0.close()

    getFullPath = os.path.dirname(firstLine)

    if os.path.exists(f"{getFullPath}\\geometry_updated.json"):
        firstLine = f"{getFullPath}\\geometry_updated.json"

    with open(firstLine, 'r') as f1:
        data = json.load(f1)

    if modelFile in data:
        key_data = data[modelFile]

        if not objects:
            messagebox.showerror("Export Error", "No objects to export.")
            return

        output_file = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialdir=os.getcwd(),
            title="Save JSON File"
        )

        if not output_file:
            return
        
        with open(output_file, 'w') as f:
            json.dump({modelFile: key_data}, f, indent=4)

        messagebox.showinfo("Notice", f"Success! Saved JSON Model to: '{output_file}'.")
    else:
        messagebox.showerror("Error", f"No Model was Found inside of JSON File called '{modelFile}'.")

def rld(newFileSet):
    model_selector['values'] = newFileSet

def reloadComboBox():
    files = os.listdir(".\\data")
    newFileSet = []
    for file in files:
        if "geometry" in file and ".txt" in file:
            newFileSet.append(file)

    rld(newFileSet)

def importBBmodel():
    global objects, current_model_file
    filename = filedialog.askopenfilename(
        defaultextension=".bbmodel",
        filetypes=[("BlockBench files", "*.bbmodel")],
        initialdir=os.getcwd(),
        title="Load BlockBench File"
    )

    if not filename:
        return

    messagebox.showinfo("Notice", "BlockBench Models are Basically Bedrock/Java Entity Models.\nJust with more information than what is theoretically needed.\nMaking them incompatible with Minecraft out of the Box.\n\nThe Application will now convert directly to Bedrock Entity.")
    
    with open(filename, 'r') as f0:
        json_string = f0.read()
        data = json.loads(json_string)

    savedFileName = data['name']
    modelName = f"geometry.{data['model_identifier']}"

    print(savedFileName)
    print(modelName)

    if 'elements' in data:
        name_count = sum(1 for element in data['elements'] if 'name' in element)

    textureWidth = data['resolution']['width']
    textureHeight = data['resolution']['height']
    fileVersion = float(data['meta']['format_version'])

    if fileVersion >= 4.31 or fileVersion < float(4):
        messagebox.showerror("Error", "BlockBench Model Format is Greater than Expected.")
        return
    
    print(textureHeight)
    print(textureWidth)

    os.makedirs(f'.\\data', exist_ok=True)
    with open(f'.\\data\\{modelName}.txt', 'w') as f1:
        for i in range(name_count):
            element = data['elements'][i]
            f1.write(f"{element['name']}\n")

            # Extracting the 'from' and 'to' values
            px, py, pz = element['from']

            origin = element['from']
            destination = element['to']

            size = [destination[j] - origin[j] for j in range(3)]
            dx, dy, dz = size
            f1.write(f"{px}, {py}, {pz}\n{dx}, {dy}, {dz}\n\n")

    bodyAndHeadItterations(1)

    reloadComboBox()
    current_model_file = f"{os.path.dirname(__file__)}\\data\\{modelName}.txt"
    objects = read_objects_from_file(current_model_file)
    object_selector.config(values=[obj.name for obj in objects])
    object_selector.set(f'')
    model_selector.set(f"{modelName}.txt")
    draw_3d_plot(objects, canvas)

def on_press(event):
    global last_x, last_y
    last_x, last_y = event.x, event.y

def on_motion(event):
    global last_x, last_y, yxFloatValue, elevation, azimuth
    if last_x is not None and last_y is not None:
        dx = event.x - last_x
        dy = event.y - last_y

        # Synchronize azimuth and elevation
        azimuth -= dx * yxFloatValue
        elevation += dy * yxFloatValue

        # Update the view
        ax.azim = azimuth
        ax.elev = elevation
        last_x, last_y = event.x, event.y

        canvas.draw()

def on_release(event):
    global last_x, last_y
    last_x, last_y = None, None

def set_drag_speed():
    global yxFloatValue
    speed = simpledialog.askfloat("Set New Mouse Speed", "Enter Mouse-Drag Speed:", initialvalue=yxFloatValue, minvalue=0.01, maxvalue=1.0)
    if speed is not None:
        yxFloatValue = speed

def set_zoom_speed():
    global inZoomFactor, outZoomFactor
    zoomMult0 = simpledialog.askfloat("Set New Zoom-In Speed", "Enter Zoom-In Speed (0.01 - 0.99):", initialvalue=inZoomFactor, minvalue=0.01, maxvalue=0.99)
    zoomMult1 = simpledialog.askfloat("Set New Zoom-Out Speed", "Enter Zoom-Out Speed (1.01 - 9.99):", initialvalue=outZoomFactor, minvalue=1.01, maxvalue=9.99)
    if zoomMult0 is not None:
        inZoomFactor = zoomMult0
    if zoomMult1 is not None:
        outZoomFactor = zoomMult1

def set_wasd_speed():
    global increaseEandA
    wasdSpeed = simpledialog.askfloat("Set New Arrow/WASD Speed", "Enter Arrow/WASD Speed (0.1 - 50):", initialvalue=increaseEandA, minvalue=0.1, maxvalue=50.0)
    if wasdSpeed is not None:
        increaseEandA = wasdSpeed

def movementWASD(event):
    global azimuth, elevation, increaseEandA

    if event.key == 'w':
        elevation += increaseEandA
    elif event.key == 's':
        elevation -= increaseEandA
    elif event.key == 'a':
        azimuth -= increaseEandA
    elif event.key == 'd':
        azimuth += increaseEandA
    elif event.key == 'p':
        elevation += increaseEandA
    elif event.key == 'down':
        elevation -= increaseEandA
    elif event.key == 'left':
        azimuth -= increaseEandA
    elif event.key == 'right':
        azimuth += increaseEandA

    # Synchronize the ax.azim and ax.elev with azimuth and elevation
    ax.view_init(elevation, azimuth)
    canvas.draw()


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
    open_menu.add_command(label="Open JSON Model", command=openJsonFile)
    open_menu.add_command(label="Open BJSON Model", command=openBjsonFile)
    open_menu.add_command(label="Open BlockBench Model", command=importBBmodel)

    save_menu = tk.Menu(file_menu, tearoff=0)
    file_menu.add_cascade(label="Save", menu=save_menu)
    save_menu.add_command(label="Save Text Model", command=save_file)
    save_menu.add_command(label="Save JSON Model", command=savetojson)
    save_menu.add_command(label="Save BJSON Model", command=savetobjson)

    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=quit_app)

    # Tools menu
    tools_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Tools", menu=tools_menu)
    scaling_menu = tk.Menu(tools_menu, tearoff=0)

    export_menu = tk.Menu(tools_menu, tearoff=0)
    export_menu.add_command(label="Export as OBJ", command=export_as_obj)
    export_menu.add_command(label="Export as STL", command=export_as_stl)
    export_menu.add_command(label="Export as PLY", command=export_as_ply)
    export_menu.add_command(label="Export as DAE", command=export_as_dae)
    export_menu.add_command(label="Export as GLTF", command=export_as_gltf)
    export_menu.add_command(label="Export as JSON", command=data2json)
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
    options_menu.add_command(label="Set Mouse Speed", command=set_drag_speed)
    options_menu.add_command(label="Set Zoom Speed", command=set_zoom_speed)
    options_menu.add_command(label="Set Arrow/WASD Speed", command=set_wasd_speed)
    options_menu.add_separator()
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

    fig = plt.figure(figsize=(8, 6))
    fig.patch.set_facecolor('darkgray')
    ax = fig.add_subplot(111, projection='3d')
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.mpl_connect('key_press_event', movementWASD)
    canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    canvas.get_tk_widget().bind("<MouseWheel>", zoom)
    canvas.get_tk_widget().bind("<ButtonPress-1>", on_press)
    canvas.get_tk_widget().bind("<B1-Motion>", on_motion)
    canvas.get_tk_widget().bind("<ButtonRelease-1>", on_release)
    canvas.get_tk_widget().bind("<MouseWheel>", zoom)

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

    update_button = tk.Button(control_panel, text="Update Text Model", command=update_object_data)
    update_button.pack(pady=10)

    model_selector.config(width=20)
    object_selector.config(width=15)

    root.mainloop()

if __name__ == "__main__":
    main()
