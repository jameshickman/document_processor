/**
 * Role-aware usage dashboard component
 * - Regular users see their own usage data via /usage/* endpoints
 * - Users with reporting role see all accounts via /reporting/* endpoints
 */

import {BaseComponent} from '../lib/component_base.js';
import { HTTP_GET, HTTP_POST_JSON } from "../lib/API.js";
import {html, css} from "lit";

export class UsageDashboard extends BaseComponent {
    static properties = {
        loading: {type: Boolean, state: true},
        reportType: {type: String, state: true},
        startDate: {type: String, state: true},
        endDate: {type: String, state: true},
        accountId: {type: Number, state: true},
        accounts: {type: Array, state: true},
        selectedTimeRange: {type: String, state: true},
        usageSummary: {type: Array, state: true},
        modelUsage: {type: Array, state: true},
        storageUsage: {type: Array, state: true},
        hasReportingRole: {type: Boolean, state: true},
        userRoles: {type: Array, state: true}
    };

    static styles = css`
        .container {
            display: flex;
            flex-direction: column;
            padding: 20px;
            font-family: Arial, sans-serif;
            height: 100%;
            overflow-y: auto;
        }

        .page-header {
            margin-bottom: 20px;
        }

        .page-header h1 {
            margin: 0 0 10px 0;
            color: #212529;
        }

        .page-header p {
            margin: 0;
            color: #6c757d;
            font-size: 14px;
        }

        .controls-panel {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 5px;
            margin-bottom: 20px;
            border: 1px solid #dee2e6;
        }

        .control-group {
            display: flex;
            flex-direction: column;
            min-width: 150px;
        }

        .control-group label {
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 5px;
            color: #495057;
        }

        .control-group input,
        .control-group select {
            padding: 8px;
            border: 1px solid #ced4da;
            border-radius: 3px;
            font-size: 14px;
        }

        .buttons-group {
            display: flex;
            gap: 10px;
            align-self: flex-end;
            margin-top: auto;
        }

        .btn {
            padding: 8px 15px;
            border: 1px solid #ccc;
            background: #fff;
            cursor: pointer;
            border-radius: 3px;
            font-size: 14px;
        }

        .btn:hover {
            background: #f0f0f0;
        }

        .btn-primary {
            background: #007bff;
            color: white;
            border-color: #007bff;
        }

        .btn-primary:hover {
            background: #0056b3;
        }

        .btn-success {
            background: #28a745;
            color: white;
            border-color: #28a745;
        }

        .btn-success:hover {
            background: #218838;
        }

        .reports-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .report-card {
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .report-card h3 {
            margin-top: 0;
            margin-bottom: 15px;
            color: #495057;
            border-bottom: 1px solid #eee;
            padding-bottom: 8px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }

        .stat-item {
            text-align: center;
            padding: 10px;
        }

        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
        }

        .stat-label {
            font-size: 12px;
            color: #6c757d;
        }

        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            background: white;
        }

        .data-table th,
        .data-table td {
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }

        .data-table th {
            background-color: #f8f9fa;
            font-weight: bold;
            color: #495057;
        }

        .data-table tr:hover {
            background-color: #f8f9fa;
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: #6c757d;
        }

        .tabs {
            display: flex;
            margin-bottom: 15px;
            border-bottom: 1px solid #dee2e6;
        }

        .tab {
            padding: 10px 20px;
            cursor: pointer;
            background: #e9ecef;
            border: 1px solid #dee2e6;
            border-bottom: none;
            border-radius: 5px 5px 0 0;
            margin-right: 5px;
        }

        .tab.active {
            background: white;
            border-bottom: 1px solid white;
            margin-bottom: -1px;
            font-weight: bold;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }
    `;

    constructor() {
        super();
        this.loading = false;
        this.reportType = 'summary';
        this.startDate = this.getDefaultStartDate();
        this.endDate = this.getDefaultEndDate();
        this.accountId = null;
        this.accounts = [];
        this.selectedTimeRange = 'last30';
        this.usageSummary = [];
        this.modelUsage = [];
        this.storageUsage = [];
        this.hasReportingRole = false;
        this.userRoles = [];
    }

    getDefaultStartDate() {
        const date = new Date();
        date.setDate(date.getDate() - 30);
        return date.toISOString().split('T')[0];
    }

    getDefaultEndDate() {
        const date = new Date();
        return date.toISOString().split('T')[0];
    }

    server_interface(api) {
        this.init_server(api);

        // Define ALL endpoints (both self-service and reporting)
        // The JWT token authentication is handled automatically by API.js
        // Role-based access control is enforced by the backend

        // Self-service endpoints
        this.server.define_endpoint(
            "/usage/my-summary",
            (resp) => {
                this.usageSummary = resp.data || [];
                this.loading = false;
                this.requestUpdate();
            },
            HTTP_POST_JSON
        );

        this.server.define_endpoint(
            "/usage/my-models",
            (resp) => {
                this.modelUsage = resp.data || [];
                this.loading = false;
                this.requestUpdate();
            },
            HTTP_POST_JSON
        );

        this.server.define_endpoint(
            "/usage/my-storage",
            (resp) => {
                this.storageUsage = resp.data || [];
                this.loading = false;
                this.requestUpdate();
            },
            HTTP_POST_JSON
        );

        // Administrative reporting endpoints
        this.server.define_endpoint(
            "/reporting/usage/summary",
            (resp) => {
                this.usageSummary = resp.data || [];
                this.loading = false;
                this.requestUpdate();
            },
            HTTP_POST_JSON
        );

        this.server.define_endpoint(
            "/reporting/usage/by-model",
            (resp) => {
                this.modelUsage = resp.data || [];
                this.loading = false;
                this.requestUpdate();
            },
            HTTP_POST_JSON
        );

        this.server.define_endpoint(
            "/reporting/storage",
            (resp) => {
                this.storageUsage = resp.data || [];
                this.loading = false;
                this.requestUpdate();
            },
            HTTP_POST_JSON
        );

        this.server.define_endpoint(
            "/reporting/accounts",
            (resp) => {
                this.accounts = resp.accounts || [];
                this.requestUpdate();
            },
            HTTP_GET
        );
    }

    checkUserRoles(jwtToken) {
        // Extract roles from JWT token
        if (jwtToken) {
            try {
                // Decode JWT (simple base64 decode of payload)
                const payload = JSON.parse(atob(jwtToken.split('.')[1]));
                this.userRoles = payload.roles || [];
                this.hasReportingRole = this.userRoles.includes('reporting') || this.userRoles.includes('admin');
                console.log('UsageDashboard: User roles detected:', this.userRoles);
                console.log('UsageDashboard: Has reporting role:', this.hasReportingRole);
            } catch (e) {
                console.error('Error decoding JWT:', e);
                this.userRoles = [];
                this.hasReportingRole = false;
            }
        }
    }

    login_success(response) {
        // Extract roles from the JWT token in the login response
        if (response && response.jwt) {
            this.checkUserRoles(response.jwt);

            // Force UI update to show/hide account selector
            this.requestUpdate();

            // Load data based on role
            if (this.hasReportingRole) {
                this.loadAccounts();
            }
            this.loadReportData();
        }
    }

    loadAccounts() {
        if (this.hasReportingRole) {
            this.server.call("/reporting/accounts", HTTP_GET);
        }
    }

    loadReportData() {
        this.loading = true;
        this.requestUpdate();

        const requestData = {
            start_date: this.startDate,
            end_date: this.endDate,
            group_by: 'day'
        };

        // Use appropriate endpoint based on role
        if (this.hasReportingRole) {
            // Add account filter if selected
            if (this.accountId) {
                requestData.account_id = this.accountId;
            }

            // Load all reports for administrators
            this.server.call("/reporting/usage/summary", HTTP_POST_JSON, requestData);
            this.server.call("/reporting/usage/by-model", HTTP_POST_JSON, requestData);
            this.server.call("/reporting/storage", HTTP_POST_JSON, requestData);
        } else {
            // Load self-service reports
            this.server.call("/usage/my-summary", HTTP_POST_JSON, requestData);
            this.server.call("/usage/my-models", HTTP_POST_JSON, requestData);
            this.server.call("/usage/my-storage", HTTP_POST_JSON, requestData);
        }
    }

    handleTimeRangeChange(e) {
        this.selectedTimeRange = e.target.value;

        const today = new Date();
        let startDate = new Date();

        switch(this.selectedTimeRange) {
            case 'last7':
                startDate.setDate(today.getDate() - 7);
                break;
            case 'last30':
                startDate.setDate(today.getDate() - 30);
                break;
            case 'last90':
                startDate.setDate(today.getDate() - 90);
                break;
            case 'month':
                startDate = new Date(today.getFullYear(), today.getMonth(), 1);
                break;
            case 'year':
                startDate = new Date(today.getFullYear(), 0, 1);
                break;
            case 'custom':
                return; // Don't auto-update for custom range
        }

        if (this.selectedTimeRange !== 'custom') {
            this.startDate = startDate.toISOString().split('T')[0];
            this.endDate = today.toISOString().split('T')[0];
            this.loadReportData();
        }
    }

    handleDateChange(e) {
        const {name, value} = e.target;
        this[name] = value;
    }

    handleAccountChange(e) {
        this.accountId = e.target.value ? parseInt(e.target.value) : null;
    }

    handleRefresh() {
        this.loadReportData();
    }

    handleExportCSV() {
        const requestData = {
            start_date: this.startDate,
            end_date: this.endDate,
            report_type: this.reportType
        };

        // Download CSV using server.download method or construct download URL
        const endpoint = this.hasReportingRole ? '/reporting/export/csv' : '/usage/my-export/csv';

        // Since we need to POST the data and get a file download, we need to handle this specially
        // The API.js doesn't have a built-in way to handle POST with file download response
        // So we'll use fetch directly with the bearer token

        const token = this.server._bearer_token || localStorage.getItem('jwt_token');
        fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(requestData)
        })
        .then(response => {
            if (!response.ok) throw new Error('Export failed');
            return response.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `usage_export_${this.startDate}_${this.endDate}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        })
        .catch(error => {
            console.error('CSV export failed:', error);
            alert('Failed to export CSV. Please try again.');
        });
    }

    renderUsageSummary() {
        if (this.usageSummary.length === 0) {
            return html`<p>No usage data available for the selected period.</p>`;
        }

        // Calculate totals
        const totals = this.usageSummary.reduce((acc, item) => ({
            operations: acc.operations + (item.total_operations || 0),
            tokens: acc.tokens + (item.total_tokens || 0),
            extractions: acc.extractions + (item.extractions || 0),
            classifications: acc.classifications + (item.classifications || 0)
        }), {operations: 0, tokens: 0, extractions: 0, classifications: 0});

        return html`
            <div class="report-card">
                <h3>Usage Summary</h3>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-value">${totals.operations.toLocaleString()}</div>
                        <div class="stat-label">Total Operations</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${totals.tokens.toLocaleString()}</div>
                        <div class="stat-label">Total Tokens</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${totals.extractions.toLocaleString()}</div>
                        <div class="stat-label">Extractions</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${totals.classifications.toLocaleString()}</div>
                        <div class="stat-label">Classifications</div>
                    </div>
                </div>
            </div>
        `;
    }

    renderModelUsage() {
        if (this.modelUsage.length === 0) {
            return html`<p>No model usage data available.</p>`;
        }

        return html`
            <div class="report-card">
                <h3>Model Usage</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Provider</th>
                            <th>Model</th>
                            <th>Operations</th>
                            <th>Tokens</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${this.modelUsage.map(item => html`
                            <tr>
                                <td>${item.provider || 'N/A'}</td>
                                <td>${item.model_name || 'N/A'}</td>
                                <td>${(item.operation_count || 0).toLocaleString()}</td>
                                <td>${(item.total_tokens || 0).toLocaleString()}</td>
                            </tr>
                        `)}
                    </tbody>
                </table>
            </div>
        `;
    }

    renderStorageUsage() {
        if (this.storageUsage.length === 0) {
            return html`<p>No storage data available.</p>`;
        }

        return html`
            <div class="report-card">
                <h3>Storage Usage</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Documents</th>
                            <th>Storage (GB)</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${this.storageUsage.map(item => html`
                            <tr>
                                <td>${item.date || 'N/A'}</td>
                                <td>${(item.document_count || 0).toLocaleString()}</td>
                                <td>${item.total_gb || 0}</td>
                            </tr>
                        `)}
                    </tbody>
                </table>
            </div>
        `;
    }

    render() {
        return html`
            <div class="container">
                <div class="page-header">
                    <h1>${this.hasReportingRole ? 'Usage Reporting' : 'My Usage'}</h1>
                    <p>${this.hasReportingRole ? 'View usage data across all accounts' : 'View your usage data and billing information'}</p>
                </div>

                <div class="controls-panel">
                    <div class="control-group">
                        <label>Time Range</label>
                        <select @change=${this.handleTimeRangeChange} .value=${this.selectedTimeRange}>
                            <option value="last7">Last 7 Days</option>
                            <option value="last30">Last 30 Days</option>
                            <option value="last90">Last 90 Days</option>
                            <option value="month">This Month</option>
                            <option value="year">This Year</option>
                            <option value="custom">Custom Range</option>
                        </select>
                    </div>

                    ${this.selectedTimeRange === 'custom' ? html`
                        <div class="control-group">
                            <label>Start Date</label>
                            <input
                                type="date"
                                name="startDate"
                                .value=${this.startDate}
                                @change=${this.handleDateChange}
                            >
                        </div>

                        <div class="control-group">
                            <label>End Date</label>
                            <input
                                type="date"
                                name="endDate"
                                .value=${this.endDate}
                                @change=${this.handleDateChange}
                            >
                        </div>
                    ` : ''}

                    ${this.hasReportingRole ? html`
                        <div class="control-group">
                            <label>Account</label>
                            <select @change=${this.handleAccountChange}>
                                <option value="">All Accounts</option>
                                ${this.accounts.map(acc => html`
                                    <option value="${acc.id}">${acc.name}</option>
                                `)}
                            </select>
                        </div>
                    ` : ''}

                    <div class="buttons-group">
                        <button class="btn btn-primary" @click=${this.handleRefresh}>Refresh</button>
                        <button class="btn btn-success" @click=${this.handleExportCSV}>Export CSV</button>
                    </div>
                </div>

                ${this.loading ? html`
                    <div class="loading">Loading usage data...</div>
                ` : html`
                    <div class="reports-container">
                        ${this.renderUsageSummary()}
                        ${this.renderModelUsage()}
                        ${this.renderStorageUsage()}
                    </div>
                `}
            </div>
        `;
    }
}

customElements.define('usage-dashboard', UsageDashboard);
