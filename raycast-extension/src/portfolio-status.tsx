import { List, ActionPanel, Action, Icon, Color } from "@raycast/api";
import { usePromise } from "@raycast/utils";
import { executePythonScript } from "./utils/python-executor";
import { ErrorView } from "./utils/error-handler.tsx";
import {
  formatCurrency,
  formatPercentage,
  formatGainLoss,
  getGainLossColor,
  formatNumber,
} from "./utils/formatters";
import { PortfolioStatusResponse, Position, CategoryData } from "./types/api";

/**
 * Fetch portfolio status from Python backend
 */
async function fetchPortfolioStatus(): Promise<PortfolioStatusResponse> {
  return await executePythonScript<PortfolioStatusResponse>("portfolio-status");
}

/**
 * Main Portfolio Status Command
 */
export default function PortfolioStatus() {
  const { data, isLoading, error, revalidate } = usePromise(fetchPortfolioStatus);

  // Handle errors
  if (error) {
    return <ErrorView error={error} onRetry={revalidate} />;
  }

  // Handle empty data
  if (!data && !isLoading) {
    return (
      <List>
        <List.EmptyView
          icon={Icon.BankNote}
          title="No Portfolio Data"
          description="Unable to fetch portfolio data. Please try again."
        />
      </List>
    );
  }

  // Calculate total values
  const totalValue = data?.data.total_value_eur || 0;
  const assetCount = data?.data.asset_count || 0;

  return (
    <List
      isLoading={isLoading}
      isShowingDetail={true}
      searchBarPlaceholder="Search positions..."
      navigationTitle={`Portfolio Status • ${formatCurrency(totalValue)}`}
    >
      {data &&
        Object.entries(data.data.categories)
          .sort(([, a], [, b]) => b.value - a.value) // Sort by value descending
          .map(([categoryName, categoryData]) => (
            <CategorySection
              key={categoryName}
              categoryName={categoryName}
              categoryData={categoryData}
              onRefresh={revalidate}
            />
          ))}

      {/* Summary item at the end */}
      {data && (
        <List.Item
          title="Total Portfolio Value"
          icon={Icon.Coins}
          accessories={[
            { text: formatCurrency(totalValue) },
            { tag: { value: `${assetCount} assets`, color: Color.Blue } },
          ]}
          detail={
            <List.Item.Detail
              metadata={
                <List.Item.Detail.Metadata>
                  <List.Item.Detail.Metadata.Label title="Portfolio Summary" />
                  <List.Item.Detail.Metadata.Separator />
                  <List.Item.Detail.Metadata.Label
                    title="Total Value"
                    text={formatCurrency(totalValue)}
                  />
                  <List.Item.Detail.Metadata.Label
                    title="Total Assets"
                    text={assetCount.toString()}
                  />
                  <List.Item.Detail.Metadata.Label
                    title="Categories"
                    text={Object.keys(data.data.categories).length.toString()}
                  />
                  <List.Item.Detail.Metadata.Separator />
                  <List.Item.Detail.Metadata.Label
                    title="Last Updated"
                    text={new Date(data.data.last_fetch).toLocaleString()}
                  />
                  <List.Item.Detail.Metadata.Label title="Data Source" text={data.data.source} />
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
      )}
    </List>
  );
}

/**
 * Category Section Component
 */
function CategorySection({
  categoryName,
  categoryData,
  onRefresh,
}: {
  categoryName: string;
  categoryData: CategoryData;
  onRefresh: () => void;
}) {
  const subtitle = `${formatCurrency(categoryData.value)} • ${formatPercentage(categoryData.percentage, false)}`;

  return (
    <List.Section title={categoryName} subtitle={subtitle}>
      {categoryData.positions
        .sort((a, b) => b.current_value_eur - a.current_value_eur) // Sort by value descending
        .map((position) => (
          <PositionItem key={position.name} position={position} category={categoryName} onRefresh={onRefresh} />
        ))}
    </List.Section>
  );
}

/**
 * Position Item Component
 */
function PositionItem({
  position,
  category,
  onRefresh,
}: {
  position: Position;
  category: string;
  onRefresh: () => void;
}) {
  const gainLossColor = getGainLossColor(position.gain_loss_eur);

  return (
    <List.Item
      title={position.name}
      subtitle={`${formatNumber(position.quantity)} shares`}
      icon={getIconForCategory(category)}
      accessories={[
        { text: formatCurrency(position.current_value_eur) },
        {
          tag: {
            value: formatPercentage(position.gain_loss_pct),
            color: gainLossColor,
          },
        },
      ]}
      detail={
        <List.Item.Detail
          metadata={
            <List.Item.Detail.Metadata>
              <List.Item.Detail.Metadata.Label title={position.name} />
              <List.Item.Detail.Metadata.Separator />
              
              {/* Current Value Section */}
              <List.Item.Detail.Metadata.Label title="Current Value" />
              <List.Item.Detail.Metadata.Label
                title="Total"
                text={formatCurrency(position.current_value_eur)}
              />
              <List.Item.Detail.Metadata.Label
                title="Quantity"
                text={`${formatNumber(position.quantity)} shares`}
              />
              <List.Item.Detail.Metadata.Separator />
              
              {/* Purchase Information */}
              <List.Item.Detail.Metadata.Label title="Purchase Information" />
              <List.Item.Detail.Metadata.Label
                title="Total Cost"
                text={formatCurrency(position.purchase_price_total_eur)}
              />
              <List.Item.Detail.Metadata.Label
                title="Cost per Share"
                text={formatCurrency(position.purchase_price_total_eur / position.quantity)}
              />
              <List.Item.Detail.Metadata.Separator />
              
              {/* Gain/Loss */}
              <List.Item.Detail.Metadata.Label title="Performance" />
              <List.Item.Detail.Metadata.Label
                title="Gain/Loss"
                text={{
                  value: formatGainLoss(position.gain_loss_eur, position.gain_loss_pct),
                  color: gainLossColor,
                }}
              />
              <List.Item.Detail.Metadata.Separator />
              
              {/* Category */}
              <List.Item.Detail.Metadata.Label title="Category" text={category} />
            </List.Item.Detail.Metadata>
          }
        />
      }
      actions={
        <ActionPanel>
          <Action.CopyToClipboard
            title="Copy Asset Name"
            content={position.name}
            shortcut={{ modifiers: ["cmd"], key: "c" }}
          />
          <Action.CopyToClipboard
            title="Copy Value"
            content={formatCurrency(position.current_value_eur)}
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

/**
 * Get icon for category
 */
function getIconForCategory(category: string): Icon {
  const categoryLower = category.toLowerCase();
  
  if (categoryLower.includes("stock")) {
    return Icon.LineChart;
  } else if (categoryLower.includes("bond")) {
    return Icon.Document;
  } else if (categoryLower.includes("etf")) {
    return Icon.BarChart;
  } else if (categoryLower.includes("cash")) {
    return Icon.BankNote;
  } else if (categoryLower.includes("pension")) {
    return Icon.Wallet;
  }
  
  return Icon.Coin;
}
