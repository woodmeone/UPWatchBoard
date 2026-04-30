# 测试代码模板

## TypeScript / JavaScript

### Jest 单元测试

```typescript
import { describe, it, expect, beforeEach, afterEach } from '@jest/globals';
import { FunctionName } from '../src/module';

describe('FunctionName', () => {
  describe('正常路径', () => {
    it('should return expected result for valid input', () => {
      const result = FunctionName('valid input');
      expect(result).toEqual('expected output');
    });
  });

  describe('异常路径', () => {
    it('should throw for invalid input', () => {
      expect(() => FunctionName('')).toThrow('error message');
    });

    it('should handle null input', () => {
      expect(() => FunctionName(null)).toThrow();
    });
  });

  describe('边界条件', () => {
    it('should handle empty array', () => {
      const result = FunctionName([]);
      expect(result).toEqual([]);
    });

    it('should handle maximum length input', () => {
      const longInput = 'a'.repeat(1000);
      const result = FunctionName(longInput);
      expect(result).toBeDefined();
    });
  });
});
```

### API 集成测试（Supertest）

```typescript
import request from 'supertest';
import { app } from '../src/app';

describe('POST /api/resource', () => {
  it('should create resource with valid data', async () => {
    const response = await request(app)
      .post('/api/resource')
      .send({ name: 'test', value: 123 })
      .expect(201);

    expect(response.body).toMatchObject({
      id: expect.any(String),
      name: 'test',
      value: 123,
    });
  });

  it('should return 400 for missing required fields', async () => {
    await request(app)
      .post('/api/resource')
      .send({})
      .expect(400);
  });

  it('should return 400 for invalid field types', async () => {
    await request(app)
      .post('/api/resource')
      .send({ name: 123, value: 'not a number' })
      .expect(400);
  });
});
```

## Python

### pytest 单元测试

```python
import pytest
from module import function_name


class TestFunctionName:
    def test_valid_input(self):
        result = function_name("valid input")
        assert result == "expected output"

    def test_empty_input_raises(self):
        with pytest.raises(ValueError, match="error message"):
            function_name("")

    def test_none_input_raises(self):
        with pytest.raises(TypeError):
            function_name(None)

    def test_boundary_max_length(self):
        long_input = "a" * 1000
        result = function_name(long_input)
        assert result is not None
```

### API 测试（pytest + httpx）

```python
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_create_resource():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/resource", json={
            "name": "test",
            "value": 123,
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test"


@pytest.mark.asyncio
async def test_create_resource_missing_fields():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/resource", json={})
        assert response.status_code == 400
```

## Go

### 标准测试

```go
package module_test

import (
    "testing"
    "module"
)

func TestFunctionName_ValidInput(t *testing.T) {
    result := module.FunctionName("valid input")
    if result != "expected output" {
        t.Errorf("expected %q, got %q", "expected output", result)
    }
}

func TestFunctionName_EmptyInput(t *testing.T) {
    _, err := module.FunctionName("")
    if err == nil {
        t.Error("expected error for empty input")
    }
}

func TestFunctionName_BoundaryMaxLength(t *testing.T) {
    longInput := strings.Repeat("a", 1000)
    result, err := module.FunctionName(longInput)
    if err != nil {
        t.Errorf("unexpected error: %v", err)
    }
    if result == "" {
        t.Error("expected non-empty result")
    }
}
```

### 表驱动测试

```go
func TestFunctionName_Table(t *testing.T) {
    tests := []struct {
        name    string
        input   string
        want    string
        wantErr bool
    }{
        {"valid input", "hello", "HELLO", false},
        {"empty input", "", "", true},
        {"special chars", "!@#", "!@#", false},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got, err := module.FunctionName(tt.input)
            if (err != nil) != tt.wantErr {
                t.Errorf("error = %v, wantErr %v", err, tt.wantErr)
                return
            }
            if got != tt.want {
                t.Errorf("got %q, want %q", got, tt.want)
            }
        })
    }
}
```
