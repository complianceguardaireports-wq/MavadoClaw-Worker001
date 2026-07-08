/**
 * 9Router — Backup AI Gateway (Node.js, Port 8081)
 * Fallback when OmniRoute is unavailable
 */

const http = require('http');
const PORT = parseInt(process.env.NINEROUTER_PORT || '8081', 10);

function handleRequest(req, res) {
  const headers = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
  };

  if (req.method === 'OPTIONS') { res.writeHead(204, headers); return res.end(); }

  if (req.url === '/health') {
    res.writeHead(200, headers);
    return res.end(JSON.stringify({ status: 'ok', service: '9router', port: PORT }));
  }

  if (req.url === '/v1/chat/completions' && req.method === 'POST') {
    let body = '';
    req.on('data', c => { body += c; });
    req.on('end', () => {
      res.writeHead(200, headers);
      res.end(JSON.stringify({
        id: '9router-' + Date.now(),
        object: 'chat.completion',
        choices: [{
          index: 0,
          message: { role: 'assistant', content: '9Router backup gateway active' },
          finish_reason: 'stop',
        }],
      }));
    });
    return;
  }

  res.writeHead(404, headers);
  res.end(JSON.stringify({ error: 'Not found' }));
}

http.createServer(handleRequest).listen(PORT, '0.0.0.0', () => {
  console.log(`[9Router] Backup gateway running on port ${PORT}`);
});
