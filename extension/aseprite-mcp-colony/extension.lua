-- aseprite-mcp-colony bridge
--
-- Connects this Aseprite editor to the local aseprite-mcp-colony MCP
-- server (Python). While connected, every Lua script the MCP would
-- normally run via `--batch --script` is sent over WebSocket and
-- executed inside this editor instead, so the user sees changes live.
--
-- Topology: Aseprite Lua has a WebSocket client (no server), so the
-- MCP process hosts the WS server and we are the client.

local WS_URL = os.getenv("ASEPRITE_MCP_URL") or "ws://127.0.0.1:12700"
local RECONNECT_INTERVAL = 5  -- seconds

local socket = nil
local connected = false
local reconnect_timer = nil
local manual_disable = false


local function log(msg)
  print(string.format("[mcp-bridge] %s", msg))
end


local function encode_response(id, result, err)
  local payload
  if err ~= nil then
    payload = { jsonrpc = "2.0", id = id, error = { code = -32000, message = tostring(err) } }
  else
    payload = { jsonrpc = "2.0", id = id, result = result }
  end
  return json.encode(payload)
end


local function ensure_active_sprite(filename)
  if not filename or filename == "" then return true, nil end
  local active = app.activeSprite
  if active and active.filename == filename then return true, nil end

  -- Look through all open sprites for a match
  for _, sprite in ipairs(app.sprites) do
    if sprite.filename == filename then
      app.activeSprite = sprite
      return true, nil
    end
  end

  -- Open the file if it exists on disk
  local f = io.open(filename, "rb")
  if f then
    f:close()
    app.command.OpenFile{ filename = filename }
    if app.activeSprite and app.activeSprite.filename == filename then
      return true, nil
    end
    return false, "failed to open " .. filename
  end

  -- File doesn't exist yet: callers like create_canvas write a new file
  -- via spr:saveAs. Don't fail here, let the script run.
  return true, nil
end


local function exec_lua(code, filename)
  local switched, switch_err = ensure_active_sprite(filename)
  if not switched then return nil, switch_err end

  local chunk, load_err = loadstring(code)
  if not chunk then return nil, "load error: " .. tostring(load_err) end

  local outputs = {}
  local original_print = print
  print = function(...)
    local parts = {}
    for i = 1, select("#", ...) do
      parts[i] = tostring(select(i, ...))
    end
    table.insert(outputs, table.concat(parts, "\t"))
  end

  local ok, result_or_err = pcall(chunk)
  print = original_print

  if not ok then return nil, "runtime error: " .. tostring(result_or_err) end

  local output = table.concat(outputs, "\n")
  if result_or_err ~= nil and result_or_err ~= "" then
    if output ~= "" then output = output .. "\n" end
    output = output .. tostring(result_or_err)
  end
  return { output = output }, nil
end


local function handle_message(message)
  local ok, req = pcall(json.decode, message)
  if not ok or type(req) ~= "table" then
    log("malformed message")
    return
  end

  local id = req.id
  local method = req.method
  local params = req.params or {}

  if method == "execute_lua" then
    local result, err = exec_lua(params.code or "", params.filename)
    if socket and connected then
      socket:sendText(encode_response(id, result, err))
    end
    return
  end

  if method == "ping" then
    if socket and connected then
      socket:sendText(encode_response(id, { pong = true }, nil))
    end
    return
  end

  if socket and connected then
    socket:sendText(encode_response(id, nil, "unknown method: " .. tostring(method)))
  end
end


local function disconnect()
  if socket then
    pcall(function() socket:close() end)
    socket = nil
  end
  connected = false
end


local function schedule_reconnect()
  if manual_disable then return end
  if reconnect_timer and reconnect_timer.isRunning then return end
  reconnect_timer = Timer{
    interval = RECONNECT_INTERVAL,
    ontick = function()
      if connected or manual_disable then
        if reconnect_timer then reconnect_timer:stop() end
        return
      end
      log("retrying connection to " .. WS_URL)
      _G.mcp_bridge_connect()
    end
  }
  reconnect_timer:start()
end


function _G.mcp_bridge_connect()
  if connected then return end
  if socket then disconnect() end

  socket = WebSocket{
    url = WS_URL,
    deflate = false,
    onreceive = function(messageType, message)
      if messageType == WebSocketMessageType.OPEN then
        connected = true
        log("connected to " .. WS_URL)
        if reconnect_timer then reconnect_timer:stop() end
      elseif messageType == WebSocketMessageType.TEXT then
        handle_message(message)
      elseif messageType == WebSocketMessageType.CLOSE then
        connected = false
        log("connection closed")
        schedule_reconnect()
      end
    end,
  }

  local ok, err = pcall(function() socket:connect() end)
  if not ok then
    log("connect failed: " .. tostring(err))
    schedule_reconnect()
  end
end


function _G.mcp_bridge_disconnect()
  manual_disable = true
  if reconnect_timer then reconnect_timer:stop() end
  disconnect()
  log("manually disconnected")
end


function _G.mcp_bridge_status()
  local state = connected and "connected" or "disconnected"
  app.alert{ title = "MCP Bridge", text = "Status: " .. state .. "\nURL: " .. WS_URL }
end


function init(plugin)
  log("init: target " .. WS_URL)

  plugin:newCommand{
    id = "MCPBridgeConnect",
    title = "MCP Bridge: Connect",
    group = "edit_undo",
    onclick = function()
      manual_disable = false
      _G.mcp_bridge_connect()
    end,
  }
  plugin:newCommand{
    id = "MCPBridgeDisconnect",
    title = "MCP Bridge: Disconnect",
    group = "edit_undo",
    onclick = _G.mcp_bridge_disconnect,
  }
  plugin:newCommand{
    id = "MCPBridgeStatus",
    title = "MCP Bridge: Status",
    group = "edit_undo",
    onclick = _G.mcp_bridge_status,
  }

  -- Auto-connect on startup
  _G.mcp_bridge_connect()
end


function exit(plugin)
  manual_disable = true
  if reconnect_timer then reconnect_timer:stop() end
  disconnect()
end
