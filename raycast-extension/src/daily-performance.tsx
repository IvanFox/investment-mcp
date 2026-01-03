import { List, ActionPanel, Action, Icon, Color } from "@raycast/api";
import { usePromise } from "@raycast/utils";
import { executePythonScript } from "./utils/python-executor";
import { ErrorView } from "./utils/error-handler.tsx";
import {
  formatCurrency,
  formatPercentage,
} from "./utils/formatters";
import { DailyPerformanceResponse, DailyPerformanceStock } from "./types/api";

/**
 * Fetch daily performance from Python backend
 */
async function fetchDailyPerformance(): Promise<DailyPerformanceResponse> {
  return await executePythonScript<DailyPerformanceResponse>("daily-performance");
}

/**
 * Main Daily Performance Command
 */
export default function DailyPerformance() {
  const { data, isLoading, error, revalidate } = usePromise(fetchDailyPerformance);

  // Handle errors
  if (error) {
    return <ErrorView error={error} onRetry={revalidate} />;
  }

  // Handle empty data
  if (!data && !isLoading) {
    return (
      <List>
        <List.EmptyView
          icon={Icon.LineChart}
          title="No Performance Data"
          description="Unable to fetch daily performance. Please try again."
        />
      </List>
    );
  }

  // Handle no stocks
  if (data && data.data.winners.length === 0 && data.data.losers.length === 0) {
    return (
      <List>
        <List.EmptyView
          icon={Icon.LineChart}
          title="No Stock Movements"
          description="No stocks with daily changes found in your portfolio."
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

  const summary = data?.data.summary;
  const subtitle = summary 
    ? `${summary.total_stocks} stocks • ${formatCurrency(summary.total_change_value_eur)} total change`
    : "";

  return (
    <List
      isLoading={isLoading}
      isShowingDetail={true}
      searchBarPlaceholder="Search stocks..."
      navigationTitle={`Daily Performance • ${subtitle}`}
    >
      {/* Winners Section */}
      {data && data.data.winners.length > 0 && (
        <List.Section 
          title="Top Winners" 
          subtitle={`${data.data.winners.length} stocks up`}
        >
          {data.data.winners.map((stock) => (
            <StockItem 
              key={`winner-${stock.name}`} 
              stock={stock} 
              onRefresh={revalidate} 
            />
          ))}
        </List.Section>
      )}

      {/* Losers Section */}
      {data && data.data.losers.length > 0 && (
        <List.Section 
          title="Top Losers" 
          subtitle={`${data.data.losers.length} stocks down`}
        >
          {data.data.losers.map((stock) => (
            <StockItem 
              key={`loser-${stock.name}`} 
              stock={stock} 
              onRefresh={revalidate} 
            />
          ))}
        </List.Section>
      )}

      {/* Summary Section */}
      {data && (
        <List.Section title="Summary">
          <List.Item
            title="Portfolio Summary"
            icon={Icon.Info}
            accessories={[
              { text: `Avg: ${formatPercentage(summary?.average_change_pct || 0)}` },
              { 
                tag: { 
                  value: formatCurrency(summary?.total_change_value_eur || 0), 
                  color: (summary?.total_change_value_eur || 0) >= 0 ? Color.Green : Color.Red 
                } 
              },
            ]}
            detail={
              <List.Item.Detail
                metadata={
                  <List.Item.Detail.Metadata>
                    <List.Item.Detail.Metadata.Label title="Daily Summary" />
                    <List.Item.Detail.Metadata.Separator />
                    <List.Item.Detail.Metadata.Label
                      title="Total Stocks"
                      text={summary?.total_stocks.toString() || "0"}
                    />
                    <List.Item.Detail.Metadata.Label
                      title="Average Change"
                      text={formatPercentage(summary?.average_change_pct || 0)}
                    />
                    <List.Item.Detail.Metadata.Label
                      title="Total Impact"
                      text={{
                        value: formatCurrency(summary?.total_change_value_eur || 0),
                        color: (summary?.total_change_value_eur || 0) >= 0 ? Color.Green : Color.Red,
                      }}
                    />
                    <List.Item.Detail.Metadata.Separator />
                    <List.Item.Detail.Metadata.Label
                      title="Winners"
                      text={`${summary?.winners_count || 0} stocks`}
                    />
                    <List.Item.Detail.Metadata.Label
                      title="Losers"
                      text={`${summary?.losers_count || 0} stocks`}
                    />
                    <List.Item.Detail.Metadata.Separator />
                    <List.Item.Detail.Metadata.Label
                      title="Last Updated"
                      text={data.data.timestamp ? new Date(data.data.timestamp).toLocaleString() : "N/A"}
                    />
                    <List.Item.Detail.Metadata.Label 
                      title="Data Source" 
                      text="Google Sheets (Live)" 
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
 * Stock Item Component
 */
function StockItem({
  stock,
  onRefresh,
}: {
  stock: DailyPerformanceStock;
  onRefresh: () => void;
}) {
  const isPositive = stock.daily_change_pct >= 0;
  const changeColor = isPositive ? Color.Green : Color.Red;
  const changeIcon = isPositive ? Icon.ArrowUp : Icon.ArrowDown;

  return (
    <List.Item
      title={stock.name}
      subtitle={stock.category}
      icon={changeIcon}
      accessories={[
        { text: formatCurrency(stock.change_value_eur), color: changeColor },
        {
          tag: {
            value: formatPercentage(stock.daily_change_pct),
            color: changeColor,
          },
        },
      ]}
      detail={
        <List.Item.Detail
          metadata={
            <List.Item.Detail.Metadata>
              <List.Item.Detail.Metadata.Label title={stock.name} />
              <List.Item.Detail.Metadata.Separator />
              
              {/* Daily Performance */}
              <List.Item.Detail.Metadata.Label title="Daily Performance" />
              <List.Item.Detail.Metadata.Label
                title="Change %"
                text={{
                  value: formatPercentage(stock.daily_change_pct),
                  color: changeColor,
                }}
              />
              <List.Item.Detail.Metadata.Label
                title="Change Value"
                text={{
                  value: formatCurrency(stock.change_value_eur),
                  color: changeColor,
                }}
              />
              <List.Item.Detail.Metadata.Separator />
              
              {/* Position Details */}
              <List.Item.Detail.Metadata.Label title="Position" />
              <List.Item.Detail.Metadata.Label
                title="Current Value"
                text={formatCurrency(stock.current_value_eur)}
              />
              <List.Item.Detail.Metadata.Label
                title="Quantity"
                text={`${stock.quantity.toFixed(2)} shares`}
              />
              <List.Item.Detail.Metadata.Separator />
              
              {/* Category */}
              <List.Item.Detail.Metadata.Label 
                title="Category" 
                text={stock.category} 
              />
            </List.Item.Detail.Metadata>
          }
        />
      }
      actions={
        <ActionPanel>
          <Action.CopyToClipboard
            title="Copy Stock Name"
            content={stock.name}
            shortcut={{ modifiers: ["cmd"], key: "c" }}
          />
          <Action.CopyToClipboard
            title="Copy Daily Change"
            content={`${stock.name}: ${formatPercentage(stock.daily_change_pct)} (${formatCurrency(stock.change_value_eur)})`}
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
