// Debug script to test the API endpoint directly
const http = require('http');

const postData = JSON.stringify({
  messages: [
    { role: "user", content: "What can I make with chickpeas?" }
  ]
});

const options = {
  hostname: 'localhost',
  port: 3000,
  path: '/api/chat',
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(postData)
  }
};

console.log('Sending request to API...');

const req = http.request(options, (res) => {
  console.log(`STATUS: ${res.statusCode}`);
  console.log(`HEADERS: ${JSON.stringify(res.headers)}`);

  let data = '';

  res.on('data', (chunk) => {
    data += chunk;
    console.log(`CHUNK: ${chunk}`);
  });

  res.on('end', () => {
    console.log('Response ended');
    console.log('Full data:', data);
  });
});

req.on('error', (e) => {
  console.error(`ERROR: ${e.message}`);
});

req.write(postData);
req.end();

// Set timeout
setTimeout(() => {
  console.log('Request timeout after 10 seconds');
  process.exit(1);
}, 10000);
