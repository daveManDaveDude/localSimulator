import { createHash } from 'node:crypto';
import { describe, expect, it } from 'vitest';
import { decodeFloat32Heightfield } from './heightfield';
import { readSyntheticFixtureBytes } from '../../tests/geo/fixtures';

function encodeFloat32(values: number[]): ArrayBuffer {
  const buffer = new ArrayBuffer(
    values.length * Float32Array.BYTES_PER_ELEMENT,
  );
  const view = new DataView(buffer);
  values.forEach((value, index) => {
    view.setFloat32(index * Float32Array.BYTES_PER_ELEMENT, value, true);
  });
  return buffer;
}

describe('decodeFloat32Heightfield', () => {
  it('decodes the generated fixture to its exact nine row-major values', () => {
    const bytes = readSyntheticFixtureBytes();
    expect(bytes.byteLength).toBe(36);
    expect(
      createHash('sha256').update(new Uint8Array(bytes)).digest('hex'),
    ).toBe('4e5e18b484af53448acdee1bffed54035c3bef7607381c3249ce255f2e2ceb14');
    expect([
      ...decodeFloat32Heightfield(bytes, { columns: 3, rows: 3 }),
    ]).toEqual([-2.5, 0, 1.25, 10, 11.5, 12, 20, 21, 22.75]);
  });

  it('reads little-endian fractional, negative and zero samples in file order', () => {
    const heights = decodeFloat32Heightfield(
      encodeFloat32([-2.5, 1.25, 0, 10.5]),
      { columns: 2, rows: 2 },
    );
    expect([...heights]).toEqual([-2.5, 1.25, 0, 10.5]);
    expect(heights).toBeInstanceOf(Float32Array);
  });

  it.each([
    [encodeFloat32([1, 2, 3]), 'does not match'],
    [new ArrayBuffer(15), 'not aligned to 4-byte'],
    [encodeFloat32([1, 2, 3, 4, 5]), 'does not match'],
  ])('rejects malformed byte length', (bytes, message) => {
    expect(() =>
      decodeFloat32Heightfield(bytes, { columns: 2, rows: 2 }),
    ).toThrow(message);
  });

  it.each([
    [Number.NaN, 'sample 1 at row 0, column 1'],
    [Number.POSITIVE_INFINITY, 'sample 1 at row 0, column 1'],
    [Number.NEGATIVE_INFINITY, 'sample 1 at row 0, column 1'],
  ])(
    'rejects non-finite sample %s with row/column context',
    (value, message) => {
      const bytes = encodeFloat32([0, value, -3, 4]);
      expect(() =>
        decodeFloat32Heightfield(bytes, { columns: 2, rows: 2 }),
      ).toThrow(message);
    },
  );

  it('returns owned data rather than a view into the downloaded bytes', () => {
    const bytes = encodeFloat32([-2.5, 0, 1.25, 10]);
    const decoded = decodeFloat32Heightfield(bytes, { columns: 2, rows: 2 });
    new DataView(bytes).setFloat32(0, 99, true);
    expect(decoded[0]).toBe(-2.5);
  });

  it.each([
    [{ columns: 1, rows: 2 }, 'columns'],
    [{ columns: 2, rows: Number.MAX_SAFE_INTEGER }, 'sample count'],
    [{ columns: 8_000_001, rows: 2 }, 'sample limit'],
  ])('rejects unsafe shape %j', (shape, message) => {
    expect(() => decodeFloat32Heightfield(new ArrayBuffer(0), shape)).toThrow(
      message,
    );
  });
});
