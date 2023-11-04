from flask import *
from fileinput import filename
from distutils.log import debug
import numpy as np
import ezdxf as ez
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import plotly.express as px
import os
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'dxf'}

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = 'tmp'


def allowed_file(filename):
  return '.' in filename and \
         filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_points_from_start_to_end(e, standard_point_scale):
  st = np.array([e.dxf.start.x, e.dxf.start.y, 0])
  ed = np.array([e.dxf.end.x, e.dxf.end.y, 0])
  st2 = np.array([e.dxf.start.x, e.dxf.start.y, 131.23])
  ed2 = np.array([e.dxf.end.x, e.dxf.end.y, 131.23])
  st3 = np.array([e.dxf.start.x, e.dxf.start.y, 78.74])
  ed3 = np.array([e.dxf.end.x, e.dxf.end.y, 78.74])

  dist_btw = np.linalg.norm(ed - st)
  dist_btw2 = np.linalg.norm(ed2 - st2)
  dist_btw3 = np.linalg.norm(ed3 - st3)
  num_points = int(dist_btw / standard_point_scale)
  num_points2 = int(dist_btw2 / standard_point_scale)
  num_points3 = int(dist_btw3 / standard_point_scale)

  # Generate intermediate points
  points = [st + i * (ed - st) / num_points for i in range(num_points)]
  points += [st2 + i * (ed2 - st2) / num_points2 for i in range(num_points2)]
  points += [st3 + i * (ed3 - st3) / num_points3 for i in range(num_points3)]
  points.append(ed)  # Add end point
  points.append(ed2)
  points.append(ed3)
  return points


def get_midpoint(e):
  st = np.array([e.dxf.start.x, e.dxf.start.y, 0])
  ed = np.array([e.dxf.end.x, e.dxf.end.y, 0])
  return (st + ed) / 2


def generate_point_cloud(dxfFile, name):
  try:
    doc = ez.readfile(dxfFile)
  except IOError:
    print("Not a DXF file or a generic I/O error.")
    return
  except ez.DXFStructureError:
    print("Invalid or corrupted DXF file.")
    return
  msp = doc.modelspace()
  standard_point_scale = 30
  labels = []

  cloud_point_array = []
  for e in msp.query('LINE[layer=="A-WALL"]'):
    cloud_point_array.extend(
      get_points_from_start_to_end(e, standard_point_scale))
    labels.append(["W"])

  door_waypoints = []
  door_labels = []
  stairs_waypoints = []
  stairs_labels = []

  for e in msp.query('LINE[layer=="A-DOOR"]'):
    door_waypoints.append(get_midpoint(e))
    door_labels.append(["D"])

  for e in msp.query('LINE[layer=="A-FLOR-STRS"]'):
    stairs_waypoints.append(get_midpoint(e))
    stairs_labels.append(["S"])

  pointCloud = np.asarray(cloud_point_array)
  pointCloudMeters = (pointCloud * 0.0254)
  df = pd.DataFrame(pointCloudMeters, columns = ['X','Y','Z'])
  x_min = df['X'].min()
  y_min = df['Y'].min()
  df['X'] -= x_min
  df['Y'] -= y_min
  pointCloudName = name + ".xyz"
  np.savetxt("tmp/" + pointCloudName, pointCloudMeters)
  fig = px.scatter_3d(df, x='X', y='Y', z='Z', color='Z', title=name)
  fig.write_html ("templates/pc.html")
  return pointCloudName


@app.route("/", methods=['GET', 'POST'])
def upload_file():
  if request.method == 'POST':
    file = request.files["file"]
    if file and allowed_file(file.filename):
      filename = secure_filename(file.filename)
      file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    return redirect(url_for('success', name=filename))
  return render_template("index.html")


@app.route("/success/<name>")
def success(name):
  file = os.path.join(app.config['UPLOAD_FOLDER'], name)
  base, ext = os.path.splitext(name)
  pointCloudName = generate_point_cloud(file, base)
  
  return render_template("Acknowledgement.html",
                         name=name,
                         pointCloudName=pointCloudName,
                        )


@app.route("/download/<pointCloudName>")
def download(pointCloudName):

  @after_this_request
  def clear_files(response):
    base, ext = os.path.splitext(pointCloudName)
    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], base + ".xyz"))
    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], base + ".dxf"))
    return response
    
  print("hello")
  print(pointCloudName)
  return send_from_directory(app.config['UPLOAD_FOLDER'], pointCloudName)


if __name__ == "__main__":
  app.run(host='0.0.0.0', debug=True)
