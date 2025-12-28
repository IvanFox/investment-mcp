import { List, ActionPanel, Action, Icon, Color } from "@raycast/api";
import { usePromise } from "@raycast/utils";
import { executePythonScript } from "./utils/python-executor";
import { ErrorView } from "./utils/error-handler.tsx";
import { formatRelativeDate, formatFullDate, groupEventsByTimePeriod } from "./utils/formatters";
import { UpcomingEventsResponse, Event } from "./types/api";

/**
 * Fetch upcoming events from Python backend
 */
async function fetchUpcomingEvents(): Promise<UpcomingEventsResponse> {
  return await executePythonScript<UpcomingEventsResponse>("upcoming-events");
}

/**
 * Main Upcoming Events Command
 */
export default function UpcomingEvents() {
  const { data, isLoading, error, revalidate } = usePromise(fetchUpcomingEvents);

  // Handle errors
  if (error) {
    return <ErrorView error={error} onRetry={revalidate} />;
  }

  // Handle empty data
  if (!data && !isLoading) {
    return (
      <List>
        <List.EmptyView
          icon={Icon.Calendar}
          title="No Events Data"
          description="Unable to fetch upcoming events. Please try again."
        />
      </List>
    );
  }

  // Handle no events
  if (data && data.data.events.length === 0) {
    return (
      <List>
        <List.EmptyView
          icon={Icon.Calendar}
          title="No Upcoming Events"
          description="No earnings reports scheduled for your portfolio stocks in the next 60 days."
          actions={
            <ActionPanel>
              <Action
                title="Refresh"
                icon={Icon.ArrowClockwise}
                onAction={revalidate}
                shortcut={{ modifiers: ["cmd"], key: "r" }}
              />
            </ActionPanel>
          }
        />
      </List>
    );
  }

  // Group events by time period
  const groupedEvents = data ? groupEventsByTimePeriod(data.data.events) : { thisWeek: [], nextWeek: [], later: [] };

  return (
    <List
      isLoading={isLoading}
      isShowingDetail={true}
      searchBarPlaceholder="Search events..."
      navigationTitle={`Upcoming Events • ${data?.data.total_events || 0} events`}
    >
      {/* This Week Section */}
      {groupedEvents.thisWeek.length > 0 && (
        <List.Section title="This Week" subtitle={`${groupedEvents.thisWeek.length} events`}>
          {groupedEvents.thisWeek.map((event, index) => (
            <EventItem key={`thisweek-${index}`} event={event} onRefresh={revalidate} />
          ))}
        </List.Section>
      )}

      {/* Next Week Section */}
      {groupedEvents.nextWeek.length > 0 && (
        <List.Section title="Next Week" subtitle={`${groupedEvents.nextWeek.length} events`}>
          {groupedEvents.nextWeek.map((event, index) => (
            <EventItem key={`nextweek-${index}`} event={event} onRefresh={revalidate} />
          ))}
        </List.Section>
      )}

      {/* Later Section */}
      {groupedEvents.later.length > 0 && (
        <List.Section title="Later" subtitle={`${groupedEvents.later.length} events`}>
          {groupedEvents.later.map((event, index) => (
            <EventItem key={`later-${index}`} event={event} onRefresh={revalidate} />
          ))}
        </List.Section>
      )}

      {/* Summary item */}
      {data && (
        <List.Section title="Summary">
          <List.Item
            title="Data Provider"
            icon={Icon.Info}
            accessories={[{ tag: { value: data.data.provider, color: Color.Blue } }]}
            detail={
              <List.Item.Detail
                metadata={
                  <List.Item.Detail.Metadata>
                    <List.Item.Detail.Metadata.Label title="Summary" />
                    <List.Item.Detail.Metadata.Separator />
                    <List.Item.Detail.Metadata.Label
                      title="Total Events"
                      text={data.data.total_events.toString()}
                    />
                    <List.Item.Detail.Metadata.Label
                      title="Earnings Reports"
                      text={data.data.earnings_count.toString()}
                    />
                    <List.Item.Detail.Metadata.Label title="Data Provider" text={data.data.provider} />
                    <List.Item.Detail.Metadata.Separator />
                    <List.Item.Detail.Metadata.Label
                      title="Last Updated"
                      text={new Date(data.metadata.timestamp).toLocaleString()}
                    />
                  </List.Item.Detail.Metadata>
                }
              />
            }
            actions={
              <ActionPanel>
                <Action
                  title="Refresh"
                  icon={Icon.ArrowClockwise}
                  onAction={revalidate}
                  shortcut={{ modifiers: ["cmd"], key: "r" }}
                />
              </ActionPanel>
            }
          />
        </List.Section>
      )}
    </List>
  );
}

/**
 * Event Item Component
 */
function EventItem({ event, onRefresh }: { event: Event; onRefresh: () => void }) {
  const relativeDate = formatRelativeDate(event.date);
  const fullDate = formatFullDate(event.date);

  // Determine color based on days until event
  let dateColor = Color.SecondaryText;
  if (event.days_until <= 3) {
    dateColor = Color.Red;
  } else if (event.days_until <= 7) {
    dateColor = Color.Orange;
  } else if (event.days_until <= 14) {
    dateColor = Color.Yellow;
  }

  return (
    <List.Item
      title={event.company_name}
      subtitle={event.type}
      icon={Icon.Calendar}
      accessories={[
        { tag: { value: event.ticker, color: Color.Blue } },
        { text: fullDate.split(",")[0] }, // Just "Month Day"
        { tag: { value: relativeDate, color: dateColor } },
      ]}
      detail={
        <List.Item.Detail
          metadata={
            <List.Item.Detail.Metadata>
              <List.Item.Detail.Metadata.Label title={event.company_name} />
              <List.Item.Detail.Metadata.Separator />

              {/* Event Information */}
              <List.Item.Detail.Metadata.Label title="Event Details" />
              <List.Item.Detail.Metadata.Label title="Ticker" text={event.ticker} />
              <List.Item.Detail.Metadata.Label title="Event Type" text={event.type} />
              <List.Item.Detail.Metadata.Separator />

              {/* Date Information */}
              <List.Item.Detail.Metadata.Label title="Date" text={fullDate} />
              <List.Item.Detail.Metadata.Label
                title="Time Until"
                text={{
                  value: relativeDate,
                  color: dateColor,
                }}
              />
              <List.Item.Detail.Metadata.Label title="Days Until" text={event.days_until.toString()} />
              <List.Item.Detail.Metadata.Separator />

              {/* Estimate (if available) */}
              {event.estimate !== undefined && event.estimate !== null && (
                <>
                  <List.Item.Detail.Metadata.Label title="Earnings Estimate" text={`$${event.estimate.toFixed(2)}`} />
                  <List.Item.Detail.Metadata.Separator />
                </>
              )}

              {/* Links */}
              <List.Item.Detail.Metadata.Link
                title="View on Yahoo Finance"
                target={`https://finance.yahoo.com/quote/${event.ticker}`}
                text={event.ticker}
              />
            </List.Item.Detail.Metadata>
          }
        />
      }
      actions={
        <ActionPanel>
          <Action.OpenInBrowser
            title="View on Yahoo Finance"
            url={`https://finance.yahoo.com/quote/${event.ticker}`}
            icon={Icon.Globe}
          />
          <Action.OpenInBrowser
            title="View Earnings Calendar"
            url={`https://finance.yahoo.com/calendar/earnings?symbol=${event.ticker}`}
            icon={Icon.Calendar}
            shortcut={{ modifiers: ["cmd", "shift"], key: "e" }}
          />
          <Action.CopyToClipboard
            title="Copy Ticker"
            content={event.ticker}
            shortcut={{ modifiers: ["cmd"], key: "c" }}
          />
          <Action.CopyToClipboard
            title="Copy Company Name"
            content={event.company_name}
            shortcut={{ modifiers: ["cmd", "shift"], key: "c" }}
          />
          <Action
            title="Refresh"
            icon={Icon.ArrowClockwise}
            onAction={onRefresh}
            shortcut={{ modifiers: ["cmd"], key: "r" }}
          />
        </ActionPanel>
      }
    />
  );
}
