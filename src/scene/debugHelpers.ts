import {
  ArrowHelper,
  BufferGeometry,
  CanvasTexture,
  Color,
  Float32BufferAttribute,
  Group,
  Line,
  LineBasicMaterial,
  LineSegments,
  Sprite,
  SpriteMaterial,
  Vector3,
} from 'three';

export type TerrainHeight = (x: number, z: number) => number;

function createLineSegments(
  positions: number[],
  color: string,
  opacity: number,
): LineSegments {
  const geometry = new BufferGeometry();
  geometry.setAttribute('position', new Float32BufferAttribute(positions, 3));
  const material = new LineBasicMaterial({
    color,
    transparent: opacity < 1,
    opacity,
    depthWrite: false,
  });

  return new LineSegments(geometry, material);
}

export function createDrapedGrid(
  width: number,
  depth: number,
  spacing: number,
  heightAt: TerrainHeight,
): LineSegments {
  const positions: number[] = [];
  const halfWidth = width / 2;
  const halfDepth = depth / 2;
  const offsetY = 0.035;

  for (let x = -halfWidth; x <= halfWidth + 0.001; x += spacing) {
    for (let z = -halfDepth; z < halfDepth; z += spacing) {
      const nextZ = Math.min(halfDepth, z + spacing);
      positions.push(x, heightAt(x, z) + offsetY, z);
      positions.push(x, heightAt(x, nextZ) + offsetY, nextZ);
    }
  }

  for (let z = -halfDepth; z <= halfDepth + 0.001; z += spacing) {
    for (let x = -halfWidth; x < halfWidth; x += spacing) {
      const nextX = Math.min(halfWidth, x + spacing);
      positions.push(x, heightAt(x, z) + offsetY, z);
      positions.push(nextX, heightAt(nextX, z) + offsetY, z);
    }
  }

  return createLineSegments(positions, '#b4d2c7', 0.22);
}

export function createWorldAxes(
  heightAt: TerrainHeight,
  axisLength = 14,
): Line[] {
  const axisY = 0.065;
  const specifications = [
    {
      from: new Vector3(0, 0, 0),
      to: new Vector3(axisLength, 0, 0),
      color: '#e59683',
    },
    {
      from: new Vector3(-axisLength, 0, 0),
      to: new Vector3(0, 0, 0),
      color: '#8f706e',
    },
    {
      from: new Vector3(0, 0, -axisLength),
      to: new Vector3(0, 0, 0),
      color: '#83c6bb',
    },
    {
      from: new Vector3(0, 0, 0),
      to: new Vector3(0, 0, axisLength),
      color: '#667f9b',
    },
  ];

  return specifications.map(({ from, to, color }) => {
    from.y = heightAt(from.x, from.z) + axisY;
    to.y = heightAt(to.x, to.z) + axisY;
    const geometry = new BufferGeometry().setFromPoints([from, to]);
    return new Line(
      geometry,
      new LineBasicMaterial({ color, depthWrite: false }),
    );
  });
}

function createNorthLabel(): Sprite | null {
  const canvas = document.createElement('canvas');
  canvas.width = 128;
  canvas.height = 128;
  const context = canvas.getContext('2d');

  if (!context) {
    return null;
  }

  context.clearRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = '#d5f3e9';
  context.font = '600 70px Segoe UI, sans-serif';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.fillText('N', canvas.width / 2, canvas.height / 2);

  const texture = new CanvasTexture(canvas);
  texture.colorSpace = 'srgb';
  const sprite = new Sprite(
    new SpriteMaterial({
      map: texture,
      color: new Color('#ffffff'),
      transparent: true,
      depthTest: false,
    }),
  );
  sprite.scale.set(1.1, 1.1, 1);
  sprite.renderOrder = 3;
  return sprite;
}

export function createNorthArrow(
  heightAt: TerrainHeight,
  position: Readonly<{ x: number; z: number }> = { x: 19, z: 12 },
  scale = 1,
): Group {
  const { x, z } = position;
  const origin = new Vector3(x, heightAt(x, z) + 0.16 * scale, z);
  const arrow = new ArrowHelper(
    new Vector3(0, 0, -1),
    origin,
    4.2 * scale,
    '#d5f3e9',
    1.1 * scale,
    0.65 * scale,
  );
  arrow.name = 'North cue pointing to -Z';
  const northCue = new Group();
  northCue.name = 'North cue pointing to -Z';
  northCue.add(arrow);
  const label = createNorthLabel();

  if (label) {
    label.scale.multiplyScalar(scale);
    label.position.set(
      x,
      heightAt(x, z - 4.9 * scale) + 0.7 * scale,
      z - 4.9 * scale,
    );
    label.name = 'North label N';
    northCue.add(label);
  }

  return northCue;
}
