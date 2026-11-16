const API_URL = "https://project-hub-api-ruby.vercel.app";

export async function getData(endpoint: string, accessToken: string) {
    const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
        }
    });

    if (!response.ok) { 
        throw new Error(`API error: ${response.status}`);
    }
    return await response.json();
}