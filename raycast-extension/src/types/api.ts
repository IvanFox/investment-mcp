/**
 * TypeScript type definitions for API responses from Python backend
 */

export interface PortfolioStatusResponse {
  success: boolean;
  data: {
    total_value_eur: number;
    asset_count: number;
    last_fetch: string;
    source: string;
    categories: {
      [categoryName: string]: CategoryData;
    };
  };
  metadata: {
    timestamp: string;
    source: string;
    data_source: string;
    read_only: boolean;
  };
}

export interface CategoryData {
  value: number;
  percentage: number;
  count: number;
  positions: Position[];
}

export interface Position {
  name: string;
  quantity: number;
  current_value_eur: number;
  purchase_price_total_eur: number;
  gain_loss_eur: number;
  gain_loss_pct: number;
}

export interface UpcomingEventsResponse {
  success: boolean;
  data: {
    events: Event[];
    total_events: number;
    earnings_count: number;
    provider: string;
  };
  metadata: {
    timestamp: string;
    source: string;
    data_source: string;
  };
}

export interface Event {
  type: string;
  ticker: string;
  company_name: string;
  date: string;
  days_until: number;
  estimate?: number;
}

export interface PythonScriptError {
  success: false;
  error: string;
  data: null;
}

export interface Preferences {
  projectRootPath: string;
}
