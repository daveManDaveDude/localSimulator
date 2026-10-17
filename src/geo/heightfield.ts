import { MAX_HEIGHTFIELD_SAMPLES } from './sceneSchema';

export interface HeightfieldShape {
  columns: number;
  rows: number;
}

function validateShape({ columns, rows }: HeightfieldShape): number {
  if (!Number.isSafeInteger(columns) || columns < 2) {
    throw new Error('heightfield.columns must be a safe integer of at least 2');
  }
  if (!Number.isSafeInteger(rows) || rows < 2) {
    throw new Error('heightfield.rows must be a safe integer of at least 2');
  }

  const sampleCount = columns * rows;
  if (!Number.isSafeInteger(sampleCount)) {
    throw new Error('heightfield sample count exceeds safe integer arithmetic');
  }
  if (sampleCount > MAX_HEIGHTFIELD_SAMPLES) {
    throw new Error(
      `heightfield sample count exceeds the ${MAX_HEIGHTFIELD_SAMPLES.toLocaleString('en-US')} sample limit`,
    );
  }

  const expectedByteLength = sampleCount * Float32Array.BYTES_PER_ELEMENT;
  if (!Number.isSafeInteger(expectedByteLength)) {
    throw new Error('heightfield byte length exceeds safe integer arithmetic');
  }
  return sampleCount;
}

/** Decode row-major little-endian float32 values without applying world offsets. */
export function decodeFloat32Heightfield(
  bytes: ArrayBuffer,
  shape: HeightfieldShape,
): Float32Array {
  const sampleCount = validateShape(shape);
  const expectedByteLength = sampleCount * Float32Array.BYTES_PER_ELEMENT;

  if (bytes.byteLength % Float32Array.BYTES_PER_ELEMENT !== 0) {
    throw new Error(
      `heightfield byte length ${bytes.byteLength} is not aligned to 4-byte float32 samples`,
    );
  }
  if (bytes.byteLength !== expectedByteLength) {
    throw new Error(
      `heightfield byte length ${bytes.byteLength} does not match ${shape.rows} × ${shape.columns} float32 samples (${expectedByteLength} bytes)`,
    );
  }

  const input = new DataView(bytes);
  const heights = new Float32Array(sampleCount);
  for (let index = 0; index < sampleCount; index += 1) {
    const value = input.getFloat32(
      index * Float32Array.BYTES_PER_ELEMENT,
      true,
    );
    if (!Number.isFinite(value)) {
      const row = Math.floor(index / shape.columns);
      const column = index % shape.columns;
      throw new Error(
        `heightfield sample ${index} at row ${row}, column ${column} is not finite`,
      );
    }
    heights[index] = value;
  }
  return heights;
}
