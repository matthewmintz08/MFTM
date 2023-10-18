from flask import *
from fileinput import filename
from distutils.log import debug
import numpy as np
import pyvista as pv
import ezdxf as ez

app = Flask(__name__)


def get_points_from_start_to_end(e, standard_point_scale):
  st = np.array([e.dxf.start.x, e.dxf.start.y, 0])
  ed = np.array([e.dxf.end.x, e.dxf.end.y, 0])

  dist_btw = np.linalg.norm(ed - st)
  num_points = int(dist_btw / standard_point_scale)

  # Generate intermediate points
  points = [st + i * (ed - st) / num_points for i in range(num_points)]
  points.append(ed)  # Add end point
  return points


def get_midpoint(e):
  st = np.array([e.dxf.start.x, e.dxf.start.y, 0])
  ed = np.array([e.dxf.end.x, e.dxf.end.y, 0])
  return (st + ed) / 2


def generate_point_cloud(dxfFile):
  try:
    doc = ez.readfile(dxfFile)
  except IOError:
    print("Not a DXF file or a generic I/O error.")
    return
  except ez.DXFStructureError:
    print("Invalid or corrupted DXF file.")
    return
  msp = doc.modelspace()
  standard_point_scale = 3
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
  print(pointCloudMeters)
  return (pointCloudMeters)
  #np.savetxt("point_cloud.xyz", pointCloud)
  np.savetxt("point_cloud_meters.xyz", pointCloudMeters)


@app.route("/")
def main():
  return render_template("index.html")


@app.route("/success", methods=['POST'])
def success():
  if request.method == 'POST':
    f = request.files['file']
    f.save(f.filename)
    generate_point_cloud(f.filename)
    return render_template("Acknowledgement.html", name=f.filename)

@app.route("/download", methods=['POST'])
def download():
  return render_template("Download.html")


if __name__ == "__main__":
  app.run(host='0.0.0.0', debug=True)
