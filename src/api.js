// Force the explicit IPv4 address to prevent the Windows localhost bug
const BASE_URL = 'http://127.0.0.1:5000/api';

export const apiScan = async (data) => {
  try {
    const response = await fetch(`${BASE_URL}/scan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Network response was not ok');
    return await response.json();
  } catch (error) {
    console.error("Error saving scan to database:", error);
    throw error;
  }
};

export const apiHistory = async () => {
  try {
    // The ?t= timestamp forces the browser to pull fresh database records!
    const response = await fetch(`${BASE_URL}/history?limit=50&t=${Date.now()}`);
    if (!response.ok) throw new Error('Network response was not ok');
    return await response.json();
  } catch (error) {
    console.error("Error fetching history:", error);
    throw error;
  }
};

export const apiDelete = async (id) => {
  try {
    const response = await fetch(`${BASE_URL}/history/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Network response was not ok');
    return await response.json();
  } catch (error) {
    console.error("Error deleting record:", error);
    throw error;
  }
};

export const apiClearHistory = async () => {
  try {
    const response = await fetch(`${BASE_URL}/history`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Network response was not ok');
    return await response.json();
  } catch (error) {
    console.error("Error clearing history:", error);
    throw error;
  }
};