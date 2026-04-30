# 代码和测试反面模式库

## 代码反面模式

### 1. 吞异常

```python
# ❌ 反面
try:
    do_something()
except:
    pass

# ✅ 正确
try:
    do_something()
except SpecificError as e:
    logger.error(f"Failed to do something: {e}")
    raise
```

### 2. 魔法数字

```typescript
// ❌ 反面
if (retryCount > 3) { ... }

// ✅ 正确
const MAX_RETRY_COUNT = 3;
if (retryCount > MAX_RETRY_COUNT) { ... }
```

### 3. 过度嵌套

```python
# ❌ 反面（3层以上嵌套）
def process(data):
    if data:
        if data.is_valid():
            if data.has_items():
                for item in data.items:
                    if item.active:
                        process_item(item)

# ✅ 正确（提前返回）
def process(data):
    if not data:
        return
    if not data.is_valid():
        return
    if not data.has_items():
        return
    for item in data.items:
        if item.active:
            process_item(item)
```

### 4. 上帝函数

```typescript
// ❌ 反面：一个函数做所有事
async function handleRequest(req: Request): Promise<Response> {
    // 200行代码：验证、查询、转换、格式化、日志...
}

// ✅ 正确：拆分为小函数
async function handleRequest(req: Request): Promise<Response> {
    const validated = validateRequest(req);
    const data = await fetchData(validated);
    const transformed = transformData(data);
    return formatResponse(transformed);
}
```

### 5. 硬编码外部依赖

```python
# ❌ 反面
response = requests.get("https://api.example.com/v1/users")

# ✅ 正确
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.example.com")
response = requests.get(f"{API_BASE_URL}/v1/users")
```

---

## 测试反面模式

### 1. 只测 happy path

```typescript
// ❌ 反面：只有正常输入
describe('parseEmail', () => {
    it('parses valid email', () => {
        expect(parseEmail('user@example.com')).toEqual({...});
    });
});

// ✅ 正确：覆盖异常和边界
describe('parseEmail', () => {
    it('parses valid email', () => { ... });
    it('throws for empty string', () => { ... });
    it('throws for missing @', () => { ... });
    it('throws for missing domain', () => { ... });
    it('handles unicode in local part', () => { ... });
});
```

### 2. 断言过于宽泛

```python
# ❌ 反面
def test_create_user():
    result = create_user("alice")
    assert result is not None  # 几乎不可能失败

# ✅ 正确
def test_create_user():
    result = create_user("alice")
    assert result.id is not None
    assert result.name == "alice"
    assert result.created_at is not None
```

### 3. 测试实现细节

```typescript
// ❌ 反面：测试私有方法
describe('UserService', () => {
    it('private hashPassword works', () => {
        const service = new UserService();
        expect(service['hashPassword']('pass')).toBe('...');
    });
});

// ✅ 正确：测试公开行为
describe('UserService', () => {
    it('creates user with hashed password', () => {
        const service = new UserService();
        const user = service.createUser('alice', 'pass');
        expect(user.passwordHash).toBeDefined();
        expect(user.passwordHash).not.toBe('pass');
    });
});
```

### 4. Mock 一切

```python
# ❌ 反面：连内部逻辑都 Mock
@patch('service.calculate_total')
@patch('service.apply_discount')
@patch('service.format_receipt')
def test_checkout(mock_format, mock_discount, mock_calc):
    mock_calc.return_value = 100
    mock_discount.return_value = 80
    mock_format.return_value = "receipt"
    result = checkout(items)
    assert result == "receipt"  # 测的是 Mock，不是代码

# ✅ 正确：只 Mock 外部依赖
@patch('service.payment_gateway.charge')
def test_checkout(mock_charge):
    mock_charge.return_value = ChargeResult(success=True)
    result = checkout(items)
    assert result.success
    assert result.total > 0
```

### 5. 测试间有依赖

```typescript
// ❌ 反面：测试依赖执行顺序
let userId: string;

it('creates user', () => {
    userId = createUser('alice').id;  // 后续测试依赖这个 userId
});

it('updates user', () => {
    updateUser(userId, { name: 'bob' });  // 如果上一个测试没跑，这个会失败
});

// ✅ 正确：每个测试独立准备数据
it('creates user', () => {
    const result = createUser('alice');
    expect(result.id).toBeDefined();
});

it('updates user', () => {
    const user = createUser('alice');  // 独立创建
    const updated = updateUser(user.id, { name: 'bob' });
    expect(updated.name).toBe('bob');
});
```

### 6. 测试无断言

```python
# ❌ 反面：没有断言，只要不报错就算通过
def test_process():
    process(data)  # 如果 process 静默失败，测试也会通过

# ✅ 正确
def test_process():
    result = process(data)
    assert result.status == "success"
    assert len(result.items) > 0
```
