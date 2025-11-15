import streamlit as st
import base64
import streamlit.components.v1 as components
from io import BytesIO
import time
import json
from streamlit_lottie import st_lottie

st.set_page_config(page_title="Dimensify - 3D Viewer", layout="centered", initial_sidebar_state="expanded")

#splash animation
def load_lottiefile(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

if "show_intro" not in st.session_state:
    st.session_state.show_intro = True

if st.session_state.show_intro:
    lottie_intro = load_lottiefile("model.json")
    splash = st.empty()
    with splash.container():
        st.markdown("<h1 style='text-align:center;'> WELCOME to DIMENSIFY</h1>", unsafe_allow_html=True)
        st_lottie(lottie_intro, height=400, speed=1.0, loop=True)
        time.sleep(3)
    splash.empty()
    st.session_state.show_intro = False

# set background
def set_local_background(image_file):
    with open(image_file, "rb") as img:
        encoded = base64.b64encode(img.read()).decode()
    css = f"""
    <style>
    html, body, .stApp {{
        background-image: url("data:image/jpg;base64,{encoded}");
        background-size: cover;
        background-repeat: no-repeat;
        background-attachment: fixed;
        background-position: center;
    }}
    [data-testid="stAppViewContainer"],
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stVerticalBlock"],
    .main, .block-container,
    .css-1d391kg, .css-18ni7ap {{
        background: transparent !important;
    }}
    
    </style>
    <div id="inspo-quote"></div>
    """
    st.markdown(css, unsafe_allow_html=True)

set_local_background("background.png")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("dimensify.png", width=600)

st.info("NOTE: This is not FINAL version of DIMENSIFY !")

# --- Sidebar controls ---
st.sidebar.markdown("")
st.sidebar.image("dimensify.png", width=400)
st.sidebar.title("Viewer Controls")
bg_color = st.sidebar.color_picker("Background color", "#2BE7D8")
model_color = st.sidebar.color_picker("Model tint (applied to STL/OBJ without textures)", "#cccccc")
wireframe = st.sidebar.checkbox("Wireframe", value=False)
show_axes = st.sidebar.checkbox("Show axes helper", value=False)
lighting_intensity = st.sidebar.slider("Lighting intensity", min_value=0.0, max_value=3.0, value=1.5, step=0.1)
auto_play_anim = st.sidebar.checkbox("Auto-play animations (GLTF)", value=True)
show_spinner = st.sidebar.checkbox("Show loading spinner", value=True)
fit_on_load = st.sidebar.checkbox("Auto-fit camera on load", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown("**Model transform**")
scale_default = st.sidebar.slider("Default scale (applied on load)", 0.1, 10.0, 1.0, 0.1)

st.sidebar.markdown("---")
st.sidebar.subheader("📂 Sample Models")
st.sidebar.markdown("[Damaged Helmet (GLB)](https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Models/master/2.0/DamagedHelmet/glTF-Binary/DamagedHelmet.glb)")
st.sidebar.markdown("[Simple OBJ (no textures)](https://people.sc.fsu.edu/~jburkardt/data/obj/teapot.obj)")
st.sidebar.markdown("---")
st.sidebar.subheader("🎨 Credits")
st.sidebar.markdown(
      """  
        - 👨‍💻 Developed by *Ansh Kunwar*  
        - ⚙️ Powered by Streamlit & Three.js
        - 🖼️ Animation by: LottieFiles
        - 🧠 GITHUB:[Source code](https://github.com/anshk1234/DIMENSIFY)
        - 📧 contact: anshkunwar3009@gmail.com                 
        - 🌐 see other projects: [streamlit.io/ansh kunwar](https://share.streamlit.io/user/anshk1234)
        - **This App is LICENSED under MIT License**
        """
    )
st.sidebar.markdown("<br><center>© 2025 DIMENSIFY</center>", unsafe_allow_html=True)


# --- File upload ---
st.info("Upload a 3D model (recommended: .obj/.glb/.gltf/.stl). For textured OBJ upload matching .mtl when prompted.")
uploaded = st.file_uploader("Upload model (.glb .gltf .obj .stl)", type=["glb", "gltf", "obj", "stl"])
mtl_uploader = None
if uploaded and uploaded.name.lower().endswith(".obj"):
    mtl_uploader = st.file_uploader("If your OBJ uses materials/textures, upload its .mtl (optional)", type=["mtl"])

if not uploaded:
    st.stop()

# Read file(s)
file_bytes = uploaded.read()
file_b64 = base64.b64encode(file_bytes).decode()
ext = uploaded.name.split(".")[-1].lower()

mtl_b64 = ""
if mtl_uploader:
    mtl_b64 = base64.b64encode(mtl_uploader.read()).decode()

# UI: Controls inside the main page (rotate, scale, reset, screenshot)
col1, col2, col3 = st.columns([1.5, 1, 1])
with col1:
    st.markdown("**Transform**")
    rotate_x = st.slider("Rotate X (deg)", -180, 180, 0, 1, key="rx")
    rotate_y = st.slider("Rotate Y (deg)", -180, 180, 0, 1, key="ry")
    rotate_z = st.slider("Rotate Z (deg)", -180, 180, 0, 1, key="rz")
with col2:
    st.markdown("**Scale & Camera**")
    scale = st.slider("Scale", 0.01, 10.0, float(scale_default), 0.01, key="scale")
    reset_cam = st.button("Reset Camera")
with col3:
    st.markdown("**Export**")
    # The actual screenshot download is implemented client-side inside the HTML (fast). Here we just show guidance.
    st.caption("Use the canvas 'Screenshot' button (on-canvas) to download PNG instantly.")

# Prepare HTML with embedded Three.js viewer and UI
html_template = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Dimensify Viewer</title>
  <style>
    html,body {{ height:100%; margin:0; overflow:hidden; background:{bg_color}; }}
    #overlay {{
        position: absolute; top:12px; left:12px; z-index:10; color:#fff; font-family:Arial, sans-serif;
        display:flex; gap:8px; align-items:center;
    }}
    #panel {{
        background: rgba(0,0,0,0.45); padding:8px 10px; border-radius:8px; backdrop-filter: blur(6px);
    }}
    #spinner {{
        position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
        z-index:9; display:flex; align-items:center; gap:10px; color:white;
        font-family:Arial, sans-serif;
    }}
    button {{
        background:#0ea5a4; color:white; border:none; padding:6px 10px; border-radius:6px; cursor:pointer;
    }}
    button.secondary {{ background:#334155; }}
    .small {{ font-size:13px; opacity:0.95; }}
  </style>
</head>
<body>
<div id="overlay">
  <div id="panel" class="small">
    <strong>Dimensify</strong> &nbsp; • &nbsp; {uploaded.name}
  </div>
  <div style="width:10px"></div>
  <div id="controls" class="small" style="display:flex; gap:8px; align-items:center;">
    <button id="screenshot">Screenshot</button>
    <button id="toggleWire" class="secondary">{'Wireframe: ON' if wireframe else 'Wireframe: OFF'}</button>
    <button id="resetBtn" class="secondary">Reset Camera</button>
    <button id="downloadModel" class="secondary">Download Model</button>
  </div>
</div>

<div id="spinner" style="display:{'flex' if show_spinner else 'none'}">
  <div style="width:30px;height:30px;border:4px solid rgba(255,255,255,0.15);border-top-color:white;border-radius:50%;animation:spin 1s linear infinite"></div>
  <div>Loading model...</div>
</div>

<canvas id="c"></canvas>

<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/OBJLoader.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/MTLLoader.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/STLLoader.js"></script>

<script>
(() => {{
  const bgColor = "{bg_color}";
  const modelColor = "{model_color}";
  const initialWire = {str(wireframe).lower()};
  const showAxes = {str(show_axes).lower()};
  const lightIntensity = {lighting_intensity};
  const autoPlay = {str(auto_play_anim).lower()};
  const fitOnLoad = {str(fit_on_load).lower()};
  const providedScale = {scale};
  const rotateXdeg = {rotate_x};
  const rotateYdeg = {rotate_y};
  const rotateZdeg = {rotate_z};

  const canvas = document.getElementById('c');
  const renderer = new THREE.WebGLRenderer({{canvas: canvas, antialias:true, preserveDrawingBuffer:true}});
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setClearColor(new THREE.Color(bgColor), 1);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(bgColor);

  const camera = new THREE.PerspectiveCamera(60, window.innerWidth/window.innerHeight, 0.01, 2000);
  camera.position.set(3,3,3);

  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;

  // Lights
  const hemi = new THREE.HemisphereLight(0xffffff, 0x444444, lightIntensity);
  scene.add(hemi);
  const dir = new THREE.DirectionalLight(0xffffff, lightIntensity*0.6);
  dir.position.set(5,10,7);
  scene.add(dir);

  // Axes helper
  let axes;
  if (showAxes) {{
    axes = new THREE.AxesHelper(1.5);
    scene.add(axes);
  }}

  let model = null;
  let mixer = null; // for animations
  let wireframeOn = initialWire;

  function applyWireframe(obj, state) {{
    obj.traverse((c) => {{
      if (c.isMesh) {{
        if (Array.isArray(c.material)) {{
          c.material.forEach(m => m.wireframe = state);
        }} else {{
          c.material.wireframe = state;
        }}
      }}
    }});
  }}

  function applyTint(obj, hex) {{
    obj.traverse((c) => {{
      if (c.isMesh && (!c.material || c.material.name === '' || c.material.map === undefined)) {{
        // apply color to non-textured meshes
        if (Array.isArray(c.material)) {{
          c.material.forEach(m => {{
            if (!m.map) m.color = new THREE.Color(hex);
          }});
        }} else {{
          if (!c.material.map) c.material.color = new THREE.Color(hex);
        }}
      }}
    }});
  }}

  function fitCameraToObject( camera, object, offset = 1.25 ) {{
    const box = new THREE.Box3().setFromObject( object );
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());

    const maxDim = Math.max(size.x, size.y, size.z);
    const fov = camera.fov * ( Math.PI / 180 );
    let cameraZ = Math.abs(maxDim / 2 * Math.tan(fov * 2));
    cameraZ *= offset;

    camera.position.set(center.x + cameraZ, center.y + cameraZ, center.z + cameraZ);
    camera.lookAt(center);
    controls.target.copy(center);
    controls.update();
  }}

  // Load model data URI
  const modelDataUri = "data:application/octet-stream;base64,{file_b64}";
  const ext = "{ext}";
  const mtlB64 = "{mtl_b64}";

  // Loaders
  const gltfLoader = new THREE.GLTFLoader();
  const objLoader = new THREE.OBJLoader();
  const mtlLoader = new THREE.MTLLoader();
  const stlLoader = new THREE.STLLoader();

  function showSpinner(state) {{
    document.getElementById('spinner').style.display = state ? 'flex' : 'none';
  }}

  showSpinner({str(show_spinner).lower()});

  async function load() {{
    try {{
      if (ext === 'glb' || ext === 'gltf') {{
        gltfLoader.load(modelDataUri, (gltf) => {{
          model = gltf.scene || gltf.scenes[0];
          model.scale.multiplyScalar(providedScale);
          scene.add(model);
          if (gltf.animations && gltf.animations.length > 0) {{
            mixer = new THREE.AnimationMixer(model);
            gltf.animations.forEach((clip) => {{
              const action = mixer.clipAction(clip);
              action.play();
            }});
            if (!autoPlay) mixer.timeScale = 0; // pause if not auto-play
          }}
          applyWireframe(model, wireframeOn);
          applyTint(model, modelColor);
          if (fitOnLoad) fitCameraToObject(camera, model, 1.2);
          showSpinner(false);
        }}, undefined, (err) => {{
          console.error(err); showSpinner(false);
        }});
      }} else if (ext === 'obj') {{
        if (mtlB64 && mtlB64 !== "") {{
          const mtlDataUri = "data:text/plain;base64," + mtlB64;
          mtlLoader.load(mtlDataUri, (materials) => {{
            materials.preload();
            objLoader.setMaterials(materials);
            objLoader.load(modelDataUri, (obj) => {{
              model = obj;
              obj.scale.multiplyScalar(providedScale);
              scene.add(obj);
              applyWireframe(obj, wireframeOn);
              applyTint(obj, modelColor);
              if (fitOnLoad) fitCameraToObject(camera, obj, 1.2);
              showSpinner(false);
            }}, undefined, (err) => {{ console.error(err); showSpinner(false); }});
          }}, undefined, (err) => {{ console.error(err); showSpinner(false); }});
        }} else {{
          objLoader.load(modelDataUri, (obj) => {{
            model = obj;
            obj.scale.multiplyScalar(providedScale);
            scene.add(obj);
            applyWireframe(obj, wireframeOn);
            applyTint(obj, modelColor);
            if (fitOnLoad) fitCameraToObject(camera, obj, 1.2);
            showSpinner(false);
          }}, undefined, (err) => {{ console.error(err); showSpinner(false); }});
        }}
      }} else if (ext === 'stl') {{
        stlLoader.load(modelDataUri, (geometry) => {{
          const mat = new THREE.MeshStandardMaterial({{color: modelColor}});
          model = new THREE.Mesh(geometry, mat);
          model.scale.multiplyScalar(providedScale);
          scene.add(model);
          applyWireframe(model, wireframeOn);
          if (fitOnLoad) fitCameraToObject(camera, model, 1.2);
          showSpinner(false);
        }}, undefined, (err) => {{ console.error(err); showSpinner(false); }});
      }} else {{
        console.error("Unsupported type:", ext);
        showSpinner(false);
      }}
    }} catch (e) {{
      console.error(e);
      showSpinner(false);
    }}
  }}

  load();

  // Animation loop
  const clock = new THREE.Clock();
  function animate() {{
    requestAnimationFrame(animate);
    const delta = clock.getDelta();
    if (mixer) mixer.update(delta);
    controls.update();
    renderer.render(scene, camera);
  }}
  animate();

  // UI interactions
  document.getElementById('screenshot').addEventListener('click', () => {{
    const dataURL = renderer.domElement.toDataURL('image/png');
    const a = document.createElement('a');
    a.href = dataURL;
    const name = "{uploaded.name}".replace(/\\.[^/.]+$/, "");
    a.download = name + "_screenshot.png";
    document.body.appendChild(a);
    a.click();
    a.remove();
  }});

  document.getElementById('toggleWire').addEventListener('click', (e) => {{
    wireframeOn = !wireframeOn;
    if (model) applyWireframe(model, wireframeOn);
    e.target.textContent = wireframeOn ? 'Wireframe: ON' : 'Wireframe: OFF';
  }});

  document.getElementById('resetBtn').addEventListener('click', () => {{
    if (model) {{
      if (fitOnLoad) fitCameraToObject(camera, model, 1.2);
      else {{ camera.position.set(3,3,3); controls.target.set(0,0,0); controls.update(); }}
    }}
  }});

  document.getElementById('downloadModel').addEventListener('click', () => {{
    const link = document.createElement('a');
    link.href = modelDataUri;
    link.download = "{uploaded.name}";
    document.body.appendChild(link);
    link.click();
    link.remove();
  }});

  // React to window resize
  window.addEventListener('resize', () => {{
    camera.aspect = window.innerWidth/window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  }});

  // Apply transform from Streamlit controls periodically by reading hidden attributes
  // We use a simple polling approach to pick up the latest transform values set by Streamlit.
  let lastTransform = {{sx:providedScale, rx:rotateXdeg, ry:rotateYdeg, rz:rotateZdeg}};
  function applyTransformsFromHost() {{
    // Polls for new values via window.name hackless approach: Streamlit re-renders the whole component on change,
    // but we can rely on small timers to pick up changes from parent (Streamlit will re-run the HTML block embedding, so
    // transforms will be injected on each rerun). For simplicity in this single-file approach we just read from variables defined above.
    if (model) {{
      model.rotation.set(THREE.MathUtils.degToRad({rotate_x}), THREE.MathUtils.degToRad({rotate_y}), THREE.MathUtils.degToRad({rotate_z}));
      model.scale.set({scale},{scale},{scale});
    }}
    requestAnimationFrame(applyTransformsFromHost);
  }}
  applyTransformsFromHost();

}})();
</script>

<style>
@keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
</style>
</body>
</html>
"""

# Render the HTML component
components.html(html_template, height=600, scrolling=False)

st.success("Viewer ready — use Download model button to get model file AND use the on-canvas controls to interact. Use the Screenshot button to download a PNG.")

st.markdown("<p style='text-align:center; color:white;'>© 2025 DIMENSIFY | Powered by Three.js </p>", unsafe_allow_html=True)


