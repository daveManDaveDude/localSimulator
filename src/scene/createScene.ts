import { Color, DirectionalLight, HemisphereLight, Scene } from 'three';

export function createScene(): Scene {
  const scene = new Scene();
  scene.background = new Color('#132027');
  scene.add(new HemisphereLight('#d8e9f0', '#354440', 1.75));

  const keyLight = new DirectionalLight('#ffe8cb', 2.8);
  keyLight.position.set(-18, 30, 22);
  scene.add(keyLight);

  return scene;
}
