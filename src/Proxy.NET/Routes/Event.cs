using System.Net;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Proxy.NET.Authentication;
using Proxy.NET.Models;
using Proxy.NET.Services;

namespace Proxy.NET.Routes;

public static class Event
{
    public static RouteGroupBuilder MapEventRoutes(this RouteGroupBuilder builder)
    {
        builder.MapPost("/eventinfo", EventInfoAsync);
        builder.MapGet("/event/{eventId}", EventRegistrationInfoAsync);
        return builder;
    }

    [Authorize(AuthenticationSchemes = ProxyAuthenticationOptions.ApiKeyScheme)]
    private static async Task<IResult> EventInfoAsync([FromServices] ICatalogService catalogService, HttpContext context)
    {
        RequestContext requestContext = (RequestContext)context.Items["RequestContext"]!;
        requestContext.DeploymentName = "event_info";
        var capabilities = await catalogService.GetCapabilities(requestContext.EventId);

        var eventInfo = new EventInfoResponse
        {
            IsAuthorized = requestContext.IsAuthorized,
            MaxTokenCap = requestContext.MaxTokenCap,
            EventCode = requestContext.EventCode,
            EventImageUrl = requestContext.EventImageUrl,
            OrganizerName = requestContext.OrganizerName,
            OrganizerEmail = requestContext.OrganizerEmail,
            Capabilities = capabilities
        };

        return TypedResults.Ok(eventInfo);
    }

    private static async Task<IResult> EventRegistrationInfoAsync(
        [FromServices] IEventService eventService,
        HttpContext context,
        string eventId
    )
    {
        var eventRegistrationInfo =
            await eventService.GetEventRegistrationInfoAsync(eventId!)
            ?? throw new HttpRequestException("Event not found", null, HttpStatusCode.NotFound);

        return TypedResults.Ok(eventRegistrationInfo);
    }
}
