const API_BASE = "http://127.0.0.1:8000";


async function loadSystem() {
    const response = await fetch(`${API_BASE}/system`);

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }

    const system = await response.json();

    document.getElementById("hostname").textContent =
        system.hostname;

    document.getElementById("cpu").textContent =
        system.cpu.toFixed(1);

    document.getElementById("memory").textContent =
        system.memory.toFixed(1);

    document.getElementById("disk").textContent =
        system.disk.toFixed(1);

    document.getElementById("system-hostname").textContent =
        system.hostname;

    document.getElementById("os").textContent =
        system.os;

    document.getElementById("kernel").textContent =
        system.kernel;

    document.getElementById("architecture").textContent =
        system.architecture;

    document.getElementById("cpu-count").textContent =
        system.cpu_count;

    document.getElementById("uptime").textContent =
        formatUptime(system.uptime);

    document.getElementById("load-1").textContent =
        system.load_average["1m"].toFixed(2);

    document.getElementById("load-5").textContent =
        system.load_average["5m"].toFixed(2);

    document.getElementById("load-15").textContent =
        system.load_average["15m"].toFixed(2);
}


let processes = [];
let selectedPid = null;
let connections = [];
let selectedConnection = null;


async function loadProcesses() {
    try {
        const response = await fetch(
            `${API_BASE}/processes`
        );

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        processes = await response.json();

        console.log("Loaded processes:", processes.length);

        renderProcesses();

    } catch (error) {
        console.error("Failed to load processes:", error);

        const table = document.getElementById(
            "process-table"
        );

        if (table) {
            table.innerHTML = `
                <tr>
                    <td colspan="5">
                        Failed to load processes
                    </td>
                </tr>
            `;
        }
    }
}


function renderProcesses() {
    const table = document.getElementById(
        "process-table"
    );

    if (!table) {
        console.error("process-table not found");
        return;
    }

    table.innerHTML = "";

    for (const process of processes) {
        const row = document.createElement("tr");

        row.innerHTML = `
            <td>${process.pid}</td>
            <td>${process.name ?? "-"}</td>
            <td>${process.username ?? "-"}</td>
            <td>${formatNumber(process.cpu)}</td>
            <td>${formatNumber(process.memory)}%</td>
        `;

        row.addEventListener("click", async () => {
            console.log("PROCESS CLICK:", process.pid);

            selectedPid = process.pid;

            showProcessSummary(process);

            await loadProcess(process.pid);
        });


        table.appendChild(row);
    }

    const count = document.getElementById(
        "process-count"
    );

    if (count) {
        count.textContent =
            `${processes.length} processes`;
    }
}


async function loadProcess(pid) {
    const detail = document.getElementById("process-detail");

    console.log("loadProcess START:", pid);

    if (!detail) {
        console.error("process-detail not found");
        return;
    }

    detail.textContent = "Loading...";

    try {
        console.log(
            "Fetching:",
            `${API_BASE}/processes/${pid}`
        );

        const response = await fetch(
            `${API_BASE}/processes/${pid}`
        );

        console.log(
            "Process response:",
            response.status
        );

        if (response.status === 404) {
            detail.innerHTML = `
                <p>Process ${pid} is no longer running.</p>
            `;

            await loadProcesses();
            return;
        }

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const process = await response.json();

        console.log(
            "Process detail loaded:",
            process
        );

        detail.innerHTML = `
            <dl>
                <dt>PID</dt>
                <dd>${process.pid}</dd>

                <dt>PPID</dt>
                <dd>${process.ppid}</dd>

                <dt>Name</dt>
                <dd>${process.name ?? "-"}</dd>

                <dt>User</dt>
                <dd>${process.username ?? "-"}</dd>

                <dt>Status</dt>
                <dd>${process.status ?? "-"}</dd>

                <dt>CPU</dt>
                <dd>${formatNumber(process.cpu)}%</dd>

                <dt>Memory</dt>
                <dd>${formatNumber(process.memory)}%</dd>

                <dt>Threads</dt>
                <dd>${process.threads ?? "-"}</dd>

                <dt>CWD</dt>
                <dd>${process.cwd ?? "-"}</dd>

                <dt>Executable</dt>
                <dd>${process.exe ?? "-"}</dd>

                <dt>Command</dt>
                <dd>${process.command ?? "-"}</dd>
            </dl>
        `;

        console.log("Process detail rendered:", pid);

    } catch (error) {
        console.error(
            "Failed to load process:",
            error
        );

        detail.innerHTML = `
            <p>Failed to load process ${pid}.</p>
        `;
    }
}


function formatNumber(value) {
    if (value === null || value === undefined) {
        return "-";
    }

    return Number(value).toFixed(2);
}


function formatUptime(seconds) {
    let remaining = seconds;

    const days = Math.floor(remaining / 86400);
    remaining %= 86400;

    const hours = Math.floor(remaining / 3600);
    remaining %= 3600;

    const minutes = Math.floor(remaining / 60);

    return `${days}d ${hours}h ${minutes}m`;
}


function showPage(page) {
    const dashboard = document.getElementById("page-dashboard");
    const processes = document.getElementById("page-processes");
    const network = document.getElementById("page-network");

    if (dashboard) {
        dashboard.hidden = page !== "dashboard";
    }

    if (processes) {
        processes.hidden = page !== "processes";
    }

    if (network) {
        network.hidden = page !== "network";
    }

    console.log("showPage:", page);
}

function setupProcessControls() {
  const search = document.getElementById("process-search");
  const sort = document.getElementById("process-sort");
  const refresh = document.getElementById("process-refresh");
  if (search) {
    search.addEventListener("input", () => {
      renderProcesses();
    });
  }
  if (sort) {
    sort.addEventListener("change", () => {
      renderProcesses();
    });
  }
  if (refresh) {
    refresh.addEventListener("click", async () => {
      await loadProcesses();
    });
  }
}

function showProcessSummary(process) {
    const detail = document.getElementById("process-detail");

    detail.innerHTML = `
        <dl>
            <dt>PID</dt>
            <dd>${process.pid}</dd>

            <dt>Name</dt>
            <dd>${process.name ?? "-"}</dd>

            <dt>User</dt>
            <dd>${process.username ?? "-"}</dd>

            <dt>CPU</dt>
            <dd>${formatNumber(process.cpu)}%</dd>

            <dt>Memory</dt>
            <dd>${formatNumber(process.memory)}%</dd>

            <dt>Status</dt>
            <dd>Checking...</dd>
        </dl>
    `;
}

function setupNavigation() {
    const links = document.querySelectorAll("[data-page]");

    console.log("Navigation links:", links.length);

    for (const link of links) {
        link.addEventListener("click", async (event) => {
            event.preventDefault();

            const page = link.dataset.page;

            console.log("Navigation clicked:", page);

            if (
                page !== "dashboard" &&
                page !== "processes" &&
                page !== "network"
            ) {
                return;
            }

            for (const item of links) {
                item.classList.remove("active");
            }

            link.classList.add("active");

            showPage(page);

            if (page === "processes") {
                await loadProcesses();
            }

            if (page === "network") {
                await loadConnections();
            }
        });
    }
}

async function loadConnections() {
    try {
        const response = await fetch(
            `${API_BASE}/network/connections`
        );

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        connections = await response.json();

        console.log(
            "Loaded connections:",
            connections.length
        );

        renderConnections();

    } catch (error) {
        console.error(
            "Failed to load network connections:",
            error
        );

        const table = document.getElementById(
            "network-table"
        );

        if (table) {
            table.innerHTML = `
                <tr>
                    <td colspan="6">
                        Failed to load network connections
                    </td>
                </tr>
            `;
        }
    }
}

function renderConnections() {
    const table = document.getElementById(
        "network-table"
    );

    if (!table) {
        return;
    }

    const search = (
        document.getElementById("network-search")?.value || ""
    ).toLowerCase();

    const status = (
        document.getElementById("network-status")?.value || ""
    );

    const filtered = connections.filter((connection) => {

        const text = [
            connection.pid,
            connection.process,
            connection.local_address,
            connection.local_port,
            connection.remote_address,
            connection.remote_port,
            connection.status
        ]
        .join(" ")
        .toLowerCase();

        if (search && !text.includes(search)) {
            return false;
        }

        if (status && connection.status !== status) {
            return false;
        }

        return true;
    });

    table.innerHTML = "";

    for (const connection of filtered) {

        const row = document.createElement("tr");

        const local =
            connection.local_address !== null
                ? `${connection.local_address}:${connection.local_port}`
                : "-";

        const remote =
            connection.remote_address !== null
                ? `${connection.remote_address}:${connection.remote_port}`
                : "-";

        row.innerHTML = `
            <td>${connection.pid}</td>
            <td>${connection.process}</td>
            <td>${connection.protocol.toUpperCase()}</td>
            <td>${local}</td>
            <td>${remote}</td>
            <td>${connection.status ?? "-"}</td>
        `;

        row.addEventListener("click", () => {
            selectedConnection = connection;

            renderConnectionDetail(connection);
        });

        table.appendChild(row);
    }

    const count = document.getElementById(
        "network-count"
    );

    if (count) {
        count.textContent =
            `${filtered.length} connections`;
    }
}

function renderConnectionDetail(connection) {

    const detail = document.getElementById(
        "network-detail"
    );

    if (!detail) {
        return;
    }

    detail.innerHTML = `
        <dl>
            <dt>PID</dt>
            <dd>${connection.pid}</dd>

            <dt>Process</dt>
            <dd>${connection.process}</dd>

            <dt>Protocol</dt>
            <dd>${connection.protocol.toUpperCase()}</dd>

            <dt>Local Address</dt>
            <dd>${connection.local_address ?? "-"}</dd>

            <dt>Local Port</dt>
            <dd>${connection.local_port ?? "-"}</dd>

            <dt>Remote Address</dt>
            <dd>${connection.remote_address ?? "-"}</dd>

            <dt>Remote Port</dt>
            <dd>${connection.remote_port ?? "-"}</dd>

            <dt>Status</dt>
            <dd>${connection.status ?? "-"}</dd>
        </dl>
    `;
}

function setupNetworkControls() {

    const search = document.getElementById("network-search");
    const status = document.getElementById("network-status");
    const refresh = document.getElementById("network-refresh");

    if (search) {
        search.addEventListener("input", () => {
            renderConnections();
        });
    }

    if (status) {
        status.addEventListener("change", () => {
            renderConnections();
        });
    }

    if (refresh) {
        refresh.addEventListener("click", async () => {
            await loadConnections();
        });
    }
}

loadSystem().catch(console.error);

setupNavigation();
setupProcessControls();
setupNetworkControls();
