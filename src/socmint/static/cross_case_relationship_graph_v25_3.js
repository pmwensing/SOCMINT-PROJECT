(() => {
  "use strict";
  const dataNode = document.getElementById("cross-case-relationship-graph-data");
  const canvas = document.getElementById("cross-case-relationship-graph-canvas");
  const selection = document.getElementById("cross-case-relationship-selection");
  if (!dataNode || !canvas || !selection) return;

  let graph;
  try {
    graph = JSON.parse(dataNode.textContent || "{}");
  } catch (error) {
    selection.textContent = `Unable to parse graph data: ${error.message}`;
    return;
  }

  const nodes = graph.nodes || [];
  const edges = graph.edges || [];
  const width = Math.max(900, nodes.length * 90);
  const height = Math.max(560, Math.ceil(nodes.length / 8) * 150);
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(height));
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Cross-case relationship graph");

  const groups = ["case", "entity", "identifier", "infrastructure", "evidence", "temporal"];
  const grouped = Object.fromEntries(groups.map((type) => [type, nodes.filter((node) => node.node_type === type)]));
  const positions = new Map();
  groups.forEach((type, columnIndex) => {
    const column = grouped[type];
    const x = 90 + columnIndex * ((width - 180) / Math.max(1, groups.length - 1));
    column.forEach((node, rowIndex) => {
      const y = 70 + rowIndex * 110;
      positions.set(node.node_id, {x, y});
    });
  });

  const show = (value) => {
    selection.textContent = JSON.stringify(value, null, 2);
  };

  edges.forEach((edge) => {
    const source = positions.get(edge.source);
    const target = positions.get(edge.target);
    if (!source || !target) return;
    const line = document.createElementNS(ns, "line");
    line.setAttribute("x1", String(source.x));
    line.setAttribute("y1", String(source.y));
    line.setAttribute("x2", String(target.x));
    line.setAttribute("y2", String(target.y));
    line.setAttribute("stroke", "currentColor");
    line.setAttribute("stroke-opacity", "0.35");
    line.setAttribute("stroke-width", "2");
    line.style.cursor = "pointer";
    line.addEventListener("click", () => show(edge));
    svg.appendChild(line);
  });

  nodes.forEach((node) => {
    const position = positions.get(node.node_id);
    if (!position) return;
    const group = document.createElementNS(ns, "g");
    group.style.cursor = "pointer";
    group.addEventListener("click", () => show(node));

    const circle = document.createElementNS(ns, "circle");
    circle.setAttribute("cx", String(position.x));
    circle.setAttribute("cy", String(position.y));
    circle.setAttribute("r", node.node_type === "case" ? "30" : "24");
    circle.setAttribute("fill", "none");
    circle.setAttribute("stroke", "currentColor");
    circle.setAttribute("stroke-width", node.node_type === "case" ? "3" : "2");
    group.appendChild(circle);

    const label = document.createElementNS(ns, "text");
    label.setAttribute("x", String(position.x));
    label.setAttribute("y", String(position.y + 48));
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("font-size", "12");
    label.textContent = node.label.length > 24 ? `${node.label.slice(0, 21)}...` : node.label;
    group.appendChild(label);

    const type = document.createElementNS(ns, "text");
    type.setAttribute("x", String(position.x));
    type.setAttribute("y", String(position.y + 4));
    type.setAttribute("text-anchor", "middle");
    type.setAttribute("font-size", "10");
    type.textContent = node.node_type;
    group.appendChild(type);

    svg.appendChild(group);
  });

  canvas.replaceChildren(svg);
})();
