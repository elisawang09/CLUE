import { LineChart } from "./linechart.js";

export async function renderRevenueChart() {

    const revenueChart = new LineChart('chart-revenue', 'data/monthly_revenue.csv', true);
    await revenueChart.renderChart();
}

