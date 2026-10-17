import type { BufferGeometry, Material, Object3D, Texture } from 'three';

/** Dispose geometries, material maps, and materials owned by an object tree. */
export function disposeSceneResources(root: Object3D): void {
  root.traverse((object) => {
    const renderable = object as typeof object & {
      geometry?: BufferGeometry;
      material?: Material | Material[];
    };

    renderable.geometry?.dispose();
    const materials = renderable.material
      ? Array.isArray(renderable.material)
        ? renderable.material
        : [renderable.material]
      : [];

    for (const material of materials) {
      const mappedMaterial = material as Material & { map?: Texture | null };
      mappedMaterial.map?.dispose();
      material.dispose();
    }
  });
}
