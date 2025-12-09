import { LineChart } from "./linechart.js";

export async function renderOrderChart() {

    const newOrderChart = new LineChart('chart-new-orders', 'data/monthly_new_customers.csv', false);
    await newOrderChart.renderChart();
}

