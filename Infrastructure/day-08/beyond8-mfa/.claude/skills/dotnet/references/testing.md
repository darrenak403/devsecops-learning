# Testing — TDD Cycle + .NET Test Patterns

TDD workflow, unit tests, integration tests, validator tests, and test data builders. Covers both the WHY (cycle) and the HOW (patterns). No API design, no security policy.

## The TDD Cycle

**RED → GREEN → REFACTOR** — always in this order.

1. **RED**: Write a failing test that describes the desired behavior
2. **GREEN**: Write the minimum code to make it pass — nothing more
3. **REFACTOR**: Clean up while keeping tests green

Never write implementation before a failing test exists.

---

## Test Framework Stack

| Tool                            | Purpose                                             |
| ------------------------------- | --------------------------------------------------- |
| **xUnit**                       | Test framework (constructor per test = fresh state) |
| **FluentAssertions**            | Readable assertions                                 |
| **Moq**                         | Mocking — always Moq, not NSubstitute               |
| **Testcontainers**              | Real PostgreSQL in integration tests                |
| **WebApplicationFactory**       | ASP.NET Core integration / E2E                      |
| **FluentValidation.TestHelper** | Validator tests                                     |

---

## Unit Test — Arrange / Act / Assert

```csharp
public class OrderServiceTests
{
    private readonly Mock<IUnitOfWork> _uow = new();
    private readonly OrderService _sut;

    private static readonly Guid OrderId = Guid.NewGuid();

    public OrderServiceTests()
    {
        _uow.Setup(u => u.SaveChangesAsync(It.IsAny<CancellationToken>())).ReturnsAsync(1);
        _sut = new OrderService(_uow.Object);
    }

    [Fact]
    public async Task GetByIdAsync_WhenNotFound_Returns404()
    {
        // Arrange
        _uow.Setup(u => u.Orders.GetByIdAsync(OrderId, It.IsAny<CancellationToken>()))
            .ReturnsAsync((Order?)null);

        // Act
        var result = await _sut.GetByIdAsync(OrderId, CancellationToken.None);

        // Assert
        result.IsSuccess.Should().BeFalse();
        result.StatusCode.Should().Be(404);
    }

    [Fact]
    public async Task CreateAsync_WhenValid_SavesAndReturns201()
    {
        _uow.Setup(u => u.Orders.AddAsync(It.IsAny<Order>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        var result = await _sut.CreateAsync(
            new CreateOrderRequest { CustomerId = "cust-1" }, CancellationToken.None);

        result.IsSuccess.Should().BeTrue();
        result.StatusCode.Should().Be(201);
        _uow.Verify(u => u.SaveChangesAsync(It.IsAny<CancellationToken>()), Times.Once);
    }
}
```

---

## Shared MockUnitOfWork Helper

For projects with many repositories, centralize mocks once:

```csharp
// tests/MyProject.Application.Tests/Helpers/MockUnitOfWork.cs
public sealed class MockUnitOfWork
{
    public Mock<IUnitOfWork> Mock { get; } = new();
    public Mock<IOrderRepository> Orders { get; } = new();
    public Mock<IProjectRepository> Projects { get; } = new();

    public MockUnitOfWork()
    {
        Mock.Setup(u => u.Orders).Returns(Orders.Object);
        Mock.Setup(u => u.Projects).Returns(Projects.Object);
        Mock.Setup(u => u.SaveChangesAsync(It.IsAny<CancellationToken>())).ReturnsAsync(1);
    }
}

// Usage
public class OrderServiceTests
{
    private readonly MockUnitOfWork _mocks = new();
    private readonly OrderService _sut;

    public OrderServiceTests() => _sut = new OrderService(_mocks.Mock.Object);
}
```

---

## Parameterized Tests — Theory

```csharp
[Theory]
[InlineData("", false)]
[InlineData("bad-email", false)]
[InlineData("user@example.com", true)]
public void IsValidEmail_ReturnsExpected(string email, bool expected)
    => EmailValidator.IsValid(email).Should().Be(expected);

// Complex cases — MemberData
[Theory]
[MemberData(nameof(InvalidOrderCases))]
public async Task CreateAsync_RejectsInvalidInput(CreateOrderRequest req, int expectedStatus)
{
    var result = await _sut.CreateAsync(req, CancellationToken.None);
    result.IsSuccess.Should().BeFalse();
    result.StatusCode.Should().Be(expectedStatus);
}

public static TheoryData<CreateOrderRequest, int> InvalidOrderCases => new()
{
    { new() { CustomerId = "" }, 400 },
    { new() { CustomerId = "c1", Items = [] }, 400 },
};
```

---

## Validator Tests

```csharp
public class CreateOrderRequestValidatorTests
{
    private readonly CreateOrderRequestValidator _validator = new();

    [Theory]
    [InlineData("")]
    [InlineData(null)]
    public void CustomerId_Empty_ShouldHaveError(string? id)
        => _validator.TestValidate(new CreateOrderRequest { CustomerId = id! })
            .ShouldHaveValidationErrorFor(x => x.CustomerId);

    [Fact]
    public void ValidRequest_ShouldPass()
        => _validator.TestValidate(new CreateOrderRequest { CustomerId = "cust-1" })
            .ShouldNotHaveAnyValidationErrors();
}
```

---

## Integration Tests — WebApplicationFactory + Testcontainers

```csharp
public class CustomWebApplicationFactory : WebApplicationFactory<Program>
{
    private static readonly PostgreSqlContainer _db = new PostgreSqlBuilder()
        .WithImage("postgres:16-alpine").Build();

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.ConfigureTestServices(services =>
        {
            services.RemoveAll<DbContextOptions<AppDbContext>>();
            services.AddDbContext<AppDbContext>(opts => opts.UseNpgsql(_db.GetConnectionString()));
            services.AddSingleton<IEmailService, NullEmailService>();
        });
    }

    public HttpClient CreateAuthenticatedClient(string role)
    {
        var client = CreateClient();
        client.DefaultRequestHeaders.Authorization =
            new("Bearer", JwtTokenHelper.GenerateTestToken(role));
        return client;
    }
}

[Collection("IntegrationTests")]
public class OrderApiTests(CustomWebApplicationFactory factory) : IClassFixture<CustomWebApplicationFactory>
{
    private readonly HttpClient _admin = factory.CreateAuthenticatedClient("Admin");
    private readonly HttpClient _anonymous = factory.CreateClient();

    [Fact]
    public async Task POST_Order_ValidRequest_Returns201()
    {
        var response = await _admin.PostAsJsonAsync("/api/v1/orders",
            new CreateOrderRequest { CustomerId = "cust-1" });
        response.StatusCode.Should().Be(HttpStatusCode.Created);
    }

    [Fact]
    public async Task POST_Order_Unauthenticated_Returns401()
        => (await _anonymous.PostAsJsonAsync("/api/v1/orders", new { }))
            .StatusCode.Should().Be(HttpStatusCode.Unauthorized);

    [Fact]
    public async Task POST_Order_WrongRole_Returns403()
    {
        var viewer = factory.CreateAuthenticatedClient("Viewer");
        (await viewer.PostAsJsonAsync("/api/v1/orders", new CreateOrderRequest { CustomerId = "c1" }))
            .StatusCode.Should().Be(HttpStatusCode.Forbidden);
    }
}
```

---

## Test Data Builder

```csharp
public sealed class OrderBuilder
{
    private string _customerId = "cust-default";
    private readonly List<OrderItem> _items = [new("SKU-001", 1, 10m)];

    public OrderBuilder WithCustomer(string id) { _customerId = id; return this; }
    public OrderBuilder WithItem(string sku, int qty, decimal price)
    {
        _items.Add(new(sku, qty, price));
        return this;
    }
    public Order Build() => new() { CustomerId = _customerId, Items = _items };
}
```

---

## Test Organization

```
tests/
  MyProject.Unit.Tests/      ← unit tests
    Services/OrderServiceTests.cs
    Validators/CreateOrderRequestValidatorTests.cs
    Helpers/MockUnitOfWork.cs
  MyProject.IntegrationTests/       ← integration tests
    Api/OrderApiTests.cs
    Infrastructure/CustomWebApplicationFactory.cs
    Infrastructure/SeedData.cs
```

---

## Anti-Patterns

| Wrong                         | Right                                                 |
| ----------------------------- | ----------------------------------------------------- |
| Write implementation first    | Tests first — always RED before GREEN                 |
| In-memory DB                  | Testcontainers (real PostgreSQL)                      |
| NSubstitute                   | Moq — stay consistent within project                  |
| Test internal state           | Test observable behavior (return values, HTTP status) |
| Tests depending on each other | Each test is fully self-contained                     |
| `Thread.Sleep`                | `Task.Delay` or polling helper                        |

---

## Running Tests

```bash
dotnet test                                               # all
dotnet test --filter "Category=Unit"                      # unit only
dotnet test --filter "Category=Integration"               # integration only
dotnet test --filter "FullyQualifiedName~OrderServiceTests" # single class
dotnet test --collect:"XPlat Code Coverage"               # with coverage
```

Coverage targets: **80%** overall, **100%** for auth/permission logic.
