import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import axios from 'axios';

const API = 'http://localhost:8000/api/nodes/';

function App() {
  const mountRef = useRef(null);
  const [graph, setGraph] = useState({ nodes: [], links: [] });

  const fetchGraph = async () => {
    const res = await axios.get(`${API}generate_graph/`);
    const nodesRes = await axios.get(API);
    setGraph({ nodes: nodesRes.data, links: [] });
  };

  useEffect(() => {
    if (!mountRef.current) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, mountRef.current.clientWidth / mountRef.current.clientHeight, 0.1, 1000);
    camera.position.z = 20;
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight);
    mountRef.current.appendChild(renderer.domElement);

    const animate = () => {
      requestAnimationFrame(animate);
      renderer.render(scene, camera);
    };
    animate();

    return () => mountRef.current.removeChild(renderer.domElement);
  }, []);

  useEffect(() => {
    // render nodes
  }, [graph]);

  return (
    <div style={{ width: '100vw', height: '100vh' }} ref={mountRef}>
      <button onClick={fetchGraph} style={{ position: 'absolute', zIndex: 10 }}>Generate Graph</button>
    </div>
  );
}

export default App;
