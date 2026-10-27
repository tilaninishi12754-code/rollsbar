import { startPreview } from '../visual/server.mjs';
const port=Number(process.argv[2]);
if(!Number.isInteger(port)||port<1024||port>65535)throw Error('Local QA port required');
const preview=await startPreview({port});
process.stdout.write(JSON.stringify({port,temp:preview.temp})+'\n');
process.stdin.once('data',async()=>{await preview.close();process.exit(0)});
