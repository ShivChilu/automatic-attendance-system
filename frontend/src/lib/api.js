import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
if (!BACKEND_URL) {
  // eslint-disable-next-line no-console
  console.warn("REACT_APP_BACKEND_URL not set; API calls will fail");
}
export const api = axios.create({ baseURL: `${BACKEND_URL}/api` });