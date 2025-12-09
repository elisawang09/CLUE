// Mock OpenAI API service
// In production, this would call your backend endpoint which calls OpenAI API

const MOCK_SUMMARIES = {
    adoption_rate: {
        description: "The adoption_rate metric measures the percentage of eligible accounts that have adopted the Team Dashboard feature by creating at least one report.",
        steps: [
            {
                title: "Source tables",
                description: "Joins feature_usage and active_accounts tables on account_id"
            },
            {
                title: "Filtering",
                description: "Filters for 'Team Dashboard' feature, 'create_report' events, and Pro/Enterprise subscription tiers"
            },
            {
                title: "Aggregation",
                description: "COUNT(DISTINCT account_id) from each table to get unique users"
            },
            {
                title: "Division",
                description: "Divides users with feature by total eligible users to calculate adoption rate"
            }
        ],
        businessContext: "This metric helps the product team track feature uptake among premium customers and identify opportunities for user engagement."
    },

    total_revenue: {
        description: "total_revenue represents the total revenue generated from all orders, aggregated monthly.",
        steps: [
            {
                title: "Product Pricing",
                description: "Raw product prices (stored in cents) are converted to dollars by dividing by 100.",
                example: "4999 cents → $49.99"
            },
            {
                title: "Order-Level Revenue",
                description: "Product prices are summed for each order, grouped by order_id.",
                example: "Order with 3 items ($49.99 + $29.99 + $19.99) = $99.97"
            },
            {
                title: "Monthly Aggregation",
                description: "Order revenues are summed by month using the order_at timestamp (truncated to month). Null values are treated as zero.",
                example: "All January 2024 orders summed = monthly total"
            }
        ],
        // data-flow: [Raw products → Staging (price conversion) → Mart (order totals) → Final (monthly aggregation)]

        // businessContext: "This metric is used for financial reporting and helps track revenue trends over time."
    },
    user_tier: {
        description: "The user_tier metric classifies users into engagement tiers (VIP, Active, At Risk, Churned) based on their activity patterns.",
        steps: [
            {
                title: "Activity metrics",
                description: "Calculates action_count_30d, sessions_last_7d, and days_since_last_action"
            },
            {
                title: "Activity score",
                description: "Weighted composite score: (action_count × 0.4) + (sessions × 0.3) + recency_bonus"
            },
            {
                title: "Tier classification",
                description: "CASE WHEN logic: VIP (score ≥ 80), Active (≥ 50), At Risk (≥ 20), Churned (else)"
            }
        ],
        businessContext: "This segmentation helps the growth team target users with appropriate engagement strategies."
    },
    sessions: {
        description: "The sessions metric tracks active user sessions by hour to understand usage patterns throughout the day.",
        steps: [
            {
                title: "Session identification",
                description: "Groups user activity events by time windows to identify distinct sessions"
            },
            {
                title: "Hourly aggregation",
                description: "COUNT of sessions grouped by hour of day"
            }
        ],
        businessContext: "Helps infrastructure team plan for peak load times and optimize resource allocation."
    }
};

export async function fetchTransformationSummary(metricName) {
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 800));

    // In production, this would be:
    // const response = await fetch('/api/transformation-summary', {
    //     method: 'POST',
    //     headers: { 'Content-Type': 'application/json' },
    //     body: JSON.stringify({ metric: metricName })
    // });
    // return await response.json();

    return MOCK_SUMMARIES[metricName] || {
        description: `Summary for ${metricName} metric.`,
        steps: [],
        businessContext: "No additional context available."
    };
}