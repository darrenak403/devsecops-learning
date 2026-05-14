# .NET Aspire — Microservice Bootstrap & Orchestration

Service bootstrap order, AppHost orchestration, service discovery, typed HTTP clients, internal service auth, and health checks. No C# language patterns (see dotnet-patterns.md), no event wiring (see events.md).

## Bootstrap Order — `Bootstrapping/ApplicationServiceExtensions.cs`

Every host project follows this exact sequence:

```csharp
public static IHostApplicationBuilder AddApplicationServices(this IHostApplicationBuilder builder)
{
    builder.AddServiceDefaults();                                         // 1. OTel, health, service discovery
    builder.AddCommonService();                                           // 2. CORS, rate limiting, MassTransit, JWT, IServiceTokenProvider
    builder.AddPostgresDatabase<MyDbContext>(Const.MyServiceDatabase);   // 3. EF Core + Npgsql (if DB needed)
    builder.AddServiceRedis(nameof(MyService), Const.Redis);             // 4. Redis (if cache needed)
    builder.Services.AddScoped<IUnitOfWork, UnitOfWork>();               // 5. DI registrations
    builder.Services.AddValidatorsFromAssemblyContaining<MyValidator>();
    return builder;
}

public static WebApplication UseApplicationServices(this WebApplication app)
{
    app.MapDefaultEndpoints();   // /health, /alive
    app.UseHttpsRedirection();
    app.UseCommonService();       // auth middleware, CORS, rate limiting
    app.MapOpenApi();
    app.MapMyModuleApi();
    return app;
}
```

**Program.cs** — run migrations + seed only in development:

```csharp
var builder = WebApplication.CreateBuilder(args);
builder.AddApplicationServices();
var app = builder.Build();
if (app.Environment.IsDevelopment()) { await app.MigrateAsync(); await app.SeedAsync(); }
app.UseApplicationServices();
app.Run();
```

---

## AppHost Orchestration

```csharp
var postgres = builder.AddPostgres("postgres").WithDataVolume().WithPgWeb();
var rabbitMq = builder.AddRabbitMQ("rabbitmq").WithManagementPlugin();
var redis    = builder.AddRedis("redis");

var orderDb = postgres.AddDatabase(Const.OrderDatabase);

builder.AddProject<Projects.MyProject_OrderService>("order-service")
    .WithReference(orderDb)
    .WithReference(rabbitMq)
    .WithReference(redis)
    .WaitFor(orderDb);
```

**Adding a new service:**
1. `var myDb = postgres.AddDatabase(Const.MyServiceDatabase);`
2. Add constant: `public const string MyServiceDatabase = "my-service-db";`
3. Register with its dependencies in AppHost
4. Add to YARP if externally accessible

---

## Service Discovery — Typed HTTP Clients

```csharp
builder.Services.AddHttpClient<IOrderClient, OrderHttpClient>(client =>
{
    var base = builder.Configuration["Services:Order:BaseUrl"];
    client.BaseAddress = new Uri(string.IsNullOrEmpty(base) ? "https+http://order-service" : base);
}).AddServiceDiscovery();
```

Service discovery name matches the AppHost registration key (e.g., `"order-service"`). The `BaseUrl` config override allows local/staging use without Aspire.

**Typed HTTP Client shape:**

```csharp
public class OrderHttpClient(HttpClient http, ILogger<OrderHttpClient> logger) : IOrderClient
{
    public async Task<OrderDto?> GetByIdAsync(Guid id, CancellationToken ct = default)
    {
        try { return await http.GetFromJsonAsync<OrderDto>($"/api/internal/orders/{id}", ct); }
        catch (Exception ex) { logger.LogError(ex, "Error fetching order {Id}", id); return null; }
    }
}
```

---

## Internal Service Authentication

Internal endpoints (`/api/internal/...`) use `IServiceTokenProvider` (registered by `AddCommonService`). Token claims `Role = "Service"`, expires in 5 minutes.

```csharp
request.Headers.Authorization = new AuthenticationHeaderValue(
    "Bearer", serviceTokenProvider.GenerateServiceToken());
```

---

## Shared Constants

```csharp
public static class Const
{
    public const string RabbitMQ            = "rabbitmq";
    public const string Redis               = "redis";
    public const string OrderDatabase       = "order-db";
    public const string CorrelationIdHeader = "X-Correlation-ID";
}
```

---

## Checklist — Adding a New Service

- [ ] Create 4 projects: `MyProject.{Service}`, `.Application`, `.Domain`, `.Infrastructure`
- [ ] Add `MyProject.{Service}.Contracts` if publishing events
- [ ] Add DB constant in shared constants class
- [ ] Create `Bootstrapping/ApplicationServiceExtensions.cs`
- [ ] Register in AppHost with resource references
- [ ] Add to YARP / API gateway if externally accessible
- [ ] Secrets in User Secrets — never in `appsettings.json`
