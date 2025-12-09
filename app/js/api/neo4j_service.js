// Mock Neo4j API service
// In production, this would call your backend endpoint which queries Neo4j

const MOCK_LINEAGE_DATA = {
    adoption_rate: {
        nodes: [
            // Layer 1: Source tables
            { id: 'dm_feature_usage', type: 'DataModel', label: 'feature_usage', layer: 1 },
            { id: 'dm_active_accounts', type: 'DataModel', label: 'active_accounts', layer: 1 },

            // Layer 1: Source columns
            { id: 'col_fu_account_id', type: 'Column', label: 'account_id', parent: 'dm_feature_usage', layer: 1 },
            { id: 'col_aa_account_id', type: 'Column', label: 'account_id', parent: 'dm_active_accounts', layer: 1 },

            // Layer 2: Join operation
            { id: 'op_join', type: 'Op', label: 'INNER JOIN', description: 'ON a.account_id = b.account_id', layer: 2 },

            // Layer 2: Joined result
            { id: 'dm_joined', type: 'DataModel', label: 'joined_data', layer: 2 },
            { id: 'col_joined_account_id_a', type: 'Column', label: 'a.account_id', parent: 'dm_joined', layer: 2 },
            { id: 'col_joined_account_id_b', type: 'Column', label: 'b.account_id', parent: 'dm_joined', layer: 2 },

            // Layer 3: Filter operation
            { id: 'op_filter', type: 'Op', label: 'WHERE', description: 'feature = \'Team Dashboard\' AND ...', layer: 3 },

            // Layer 3: Filtered result
            { id: 'dm_filtered', type: 'DataModel', label: 'filtered_data', layer: 3 },
            { id: 'col_filtered_account_id_a', type: 'Column', label: 'a.account_id', parent: 'dm_filtered', layer: 3 },
            { id: 'col_filtered_account_id_b', type: 'Column', label: 'b.account_id', parent: 'dm_filtered', layer: 3 },

            // Layer 4: Aggregation operations
            { id: 'op_count_a', type: 'Op', label: 'COUNT(DISTINCT)', description: 'a.account_id', layer: 4 },
            { id: 'op_count_b', type: 'Op', label: 'COUNT(DISTINCT)', description: 'b.account_id', layer: 4 },

            // Layer 4: Aggregated columns
            { id: 'col_count_a', type: 'Column', label: 'users_with_feature', parent: null, layer: 4 },
            { id: 'col_count_b', type: 'Column', label: 'total_eligible', parent: null, layer: 4 },

            // Layer 5: Division operation
            { id: 'op_divide', type: 'Op', label: '÷', description: 'Division', layer: 5 },

            // Layer 5: Output
            { id: 'dm_output', type: 'DataModel', label: 'query_result', layer: 5 },
            { id: 'col_adoption_rate', type: 'Column', label: 'adoption_rate', parent: 'dm_output', layer: 5 }
        ],
        links: [
            // Layer 1 to 2: Columns to JOIN
            { source: 'col_fu_account_id', target: 'op_join' },
            { source: 'col_aa_account_id', target: 'op_join' },
            { source: 'op_join', target: 'col_joined_account_id_a' },
            { source: 'op_join', target: 'col_joined_account_id_b' },

            // Layer 2 to 3: Joined columns to FILTER
            { source: 'col_joined_account_id_a', target: 'op_filter' },
            { source: 'col_joined_account_id_b', target: 'op_filter' },
            { source: 'op_filter', target: 'col_filtered_account_id_a' },
            { source: 'op_filter', target: 'col_filtered_account_id_b' },

            // Layer 3 to 4: Filtered columns to COUNT operations
            { source: 'col_filtered_account_id_a', target: 'op_count_a' },
            { source: 'col_filtered_account_id_b', target: 'op_count_b' },
            { source: 'op_count_a', target: 'col_count_a' },
            { source: 'op_count_b', target: 'col_count_b' },

            // Layer 4 to 5: Counts to DIVIDE
            { source: 'col_count_a', target: 'op_divide' },
            { source: 'col_count_b', target: 'op_divide' },
            { source: 'op_divide', target: 'col_adoption_rate' }
        ],
        layers: [
            { index: 1, label: 'SOURCES' },
            { index: 2, label: 'JOIN' },
            { index: 3, label: 'FILTER' },
            { index: 4, label: 'AGGREGATE' },
            { index: 5, label: 'OUTPUT' }
        ]
    },
    // Add other metrics as needed
    total_revenue: {
        nodes: [
            // Layer 1: Raw sources
            { id: 'dm_raw_products', type: 'DataModel', label: 'raw_products', layer: 1 },
            { id: 'dm_raw_orders', type: 'DataModel', label: 'raw_orders', layer: 1 },
            { id: 'col_raw_price', type: 'Column', label: 'price', parent: 'dm_raw_products', layer: 1 },
            { id: 'col_raw_order_id', type: 'Column', label: 'order_id', parent: 'dm_raw_orders', layer: 1 },
            { id: 'col_raw_order_at', type: 'Column', label: 'order_at', parent: 'dm_raw_orders', layer: 1 },

            // Layer 2: Staging - Price conversion
            { id: 'op_divide', type: 'Op', label: '÷', description: '÷ 100', layer: 2 },
            { id: 'dm_stg_product', type: 'DataModel', label: 'stg_product', layer: 2 },
            { id: 'col_stg_product_price', type: 'Column', label: 'product_price', parent: 'dm_stg_product', layer: 2 },

            // Layer 2: Staging - Order items
            { id: 'dm_stg_order_items', type: 'DataModel', label: 'stg_order_items', layer: 2 },
            { id: 'col_stg_product_price_items', type: 'Column', label: 'product_price', parent: 'dm_stg_order_items', layer: 2 },
            { id: 'col_stg_order_id', type: 'Column', label: 'order_id', parent: 'dm_stg_order_items', layer: 2 },

            // Layer 3: Mart - Order-level aggregation
            { id: 'op_sum_order', type: 'Op', label: 'SUM', description: 'sum(product_price) GROUP BY order_id', layer: 3 },
            { id: 'dm_mart_orders', type: 'DataModel', label: 'mart_orders', layer: 3 },
            { id: 'col_mart_revenue', type: 'Column', label: 'revenue', parent: 'dm_mart_orders', layer: 3 },
            { id: 'col_mart_order_at', type: 'Column', label: 'order_at', parent: 'dm_mart_orders', layer: 3 },

            // Layer 4: Final aggregation
            { id: 'op_coalesce_sum', type: 'Op', label: 'SUM(COALESCE)', description: 'sum(coalesce(revenue, 0)) GROUP BY trunc(order_at, MONTH)', layer: 4 },

            // Layer 5: Output
            { id: 'dm_output', type: 'DataModel', label: 'query_result', layer: 5 },
            { id: 'col_total_revenue', type: 'Column', label: 'total_revenue', parent: 'dm_output', layer: 5 }
        ],
        links: [
            // Layer 1 to 2: Price conversion
            { source: 'col_raw_price', target: 'op_divide' },
            { source: 'op_divide', target: 'col_stg_product_price', label: 'output as' },
            { source: 'col_raw_order_id', target: 'col_stg_order_id' },

            // Layer 2: Product price flows to order items
            { source: 'col_stg_product_price', target: 'col_stg_product_price_items'},

            // Layer 2 to 3: Order-level aggregation
            { source: 'col_stg_product_price_items', target: 'op_sum_order' },
            { source: 'col_stg_order_id', target: 'op_sum_order' },
            { source: 'op_sum_order', target: 'col_mart_revenue', label: 'output as' },

            // Layer 1 to 3: Order timestamp flows through
            { source: 'col_raw_order_at', target: 'col_mart_order_at' },

            // Layer 3 to 4: Final monthly aggregation
            { source: 'col_mart_revenue', target: 'op_coalesce_sum' },
            { source: 'col_mart_order_at', target: 'op_coalesce_sum' },

            // Layer 4 to 5: Output
            { source: 'op_coalesce_sum', target: 'col_total_revenue' }
        ],
        layers: [
            { index: 1, label: 'RAW' },
            { index: 2, label: 'STAGING' },
            { index: 3, label: 'MART' },
            { index: 4, label: 'AGGREGATE' },
            { index: 5, label: 'OUTPUT' }
        ]
    }
};

export async function fetchLineageData(metricName) {
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 600));

    // In production, this would be:
    // const response = await fetch('/api/lineage', {
    //     method: 'POST',
    //     headers: { 'Content-Type': 'application/json' },
    //     body: JSON.stringify({ metric: metricName })
    // });
    // return await response.json();

    return MOCK_LINEAGE_DATA[metricName] || MOCK_LINEAGE_DATA.adoption_rate;
}