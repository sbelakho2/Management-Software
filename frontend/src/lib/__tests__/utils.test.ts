import { cn, formatDate, formatCurrency, formatNumber, getInitials, truncate } from '../utils';

describe('cn (classnames utility)', () => {
  it('should merge class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar');
  });

  it('should handle conditional classes', () => {
    expect(cn('foo', false && 'bar', 'baz')).toBe('foo baz');
  });

  it('should merge tailwind classes correctly', () => {
    expect(cn('px-2 py-1', 'px-4')).toBe('py-1 px-4');
  });

  it('should handle undefined and null values', () => {
    expect(cn('foo', undefined, null, 'bar')).toBe('foo bar');
  });

  it('should handle object notation', () => {
    expect(cn({ foo: true, bar: false, baz: true })).toBe('foo baz');
  });

  it('should handle array inputs', () => {
    expect(cn(['foo', 'bar'])).toBe('foo bar');
  });
});

describe('formatDate', () => {
  it('should format date with default options', () => {
    const date = new Date('2024-01-15T00:00:00.000Z');
    const result = formatDate(date);
    expect(result).toContain('Jan');
    expect(result).toContain('15');
    expect(result).toContain('2024');
  });

  it('should handle string dates', () => {
    const result = formatDate('2024-01-15');
    expect(result).toContain('15');
  });

  it('should respect custom options', () => {
    const date = new Date('2024-01-15T00:00:00.000Z');
    const result = formatDate(date, { month: 'short', day: 'numeric' });
    expect(result).toContain('Jan');
    expect(result).toContain('15');
  });
});

describe('formatCurrency', () => {
  it('should format currency in MAD', () => {
    const result = formatCurrency(1234.56);
    // fr-MA locale formats as "1.234,56 MAD"
    expect(result).toContain('1');
    expect(result).toContain('234');
    expect(result).toContain('56');
    expect(result).toContain('MAD');
  });

  it('should handle zero', () => {
    const result = formatCurrency(0);
    expect(result).toContain('0');
  });

  it('should handle negative numbers', () => {
    const result = formatCurrency(-1000);
    expect(result).toContain('1');
    expect(result).toContain('000');
  });

  it('should handle large numbers', () => {
    const result = formatCurrency(1000000);
    expect(result).toContain('1');
  });
});

describe('formatNumber', () => {
  it('should format numbers with locale', () => {
    const result = formatNumber(1234567);
    // en-US locale formats as "1,234,567"
    expect(result).toBe('1,234,567');
  });

  it('should handle decimals', () => {
    const result = formatNumber(1234.56);
    expect(result).toContain('234');
  });

  it('should handle zero', () => {
    const result = formatNumber(0);
    expect(result).toBe('0');
  });
});

describe('getInitials', () => {
  it('should get initials from full name', () => {
    expect(getInitials('John Doe')).toBe('JD');
  });

  it('should handle single name', () => {
    expect(getInitials('John')).toBe('J');
  });

  it('should handle multiple names', () => {
    // getInitials takes first letter of each word, then slices to 2
    // "John Paul Jones" → "JPJ" → "JP"
    expect(getInitials('John Paul Jones')).toBe('JP');
  });

  it('should handle empty string', () => {
    expect(getInitials('')).toBe('');
  });

  it('should handle lowercase names', () => {
    expect(getInitials('john doe')).toBe('JD');
  });
});

describe('truncate', () => {
  it('should truncate long strings', () => {
    const result = truncate('This is a very long string that should be truncated', 20);
    expect(result).toBe('This is a very long ...');
    expect(result.length).toBe(23); // 20 chars + '...'
  });

  it('should not truncate short strings', () => {
    const result = truncate('Short', 20);
    expect(result).toBe('Short');
  });

  it('should handle exact length', () => {
    const result = truncate('Exactly20Characters!', 20);
    expect(result).toBe('Exactly20Characters!');
  });

  it('should handle empty string', () => {
    const result = truncate('', 20);
    expect(result).toBe('');
  });
});
