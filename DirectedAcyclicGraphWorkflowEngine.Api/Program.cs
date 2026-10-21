using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using DirectedAcyclicGraphWorkflowEngine.Core;
using DirectedAcyclicGraphWorkflowEngine.Api.Hubs;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

builder.Services.AddSingleton<MissionManager>();

builder.Services.AddSignalR();

var app = builder.Build();

app.UseCors(policy => policy
    .SetIsOriginAllowed(origin => true)
    .AllowAnyMethod()
    .AllowAnyHeader()
    .AllowCredentials());

app.UseSwagger(); 
app.UseSwaggerUI();
app.UseWebSockets();

app.MapControllers();

app.MapHub<EngineHub>("/engine-socket");

app.Run();