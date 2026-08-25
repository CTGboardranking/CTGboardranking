export default async function handler(req, res) {

    if (req.method !== "POST") {
        return res.status(405).json({
            error: "Method not allowed"
        });
    }

    try {

        const url = process.env.SUPABASE_URL;
        const key = process.env.SUPABASE_KEY;

        if (!url || !key) {

            console.error(
                "Missing SUPABASE_URL or SUPABASE_KEY"
            );

            return res.status(500).json({
                error: "Supabase environment variables are missing"
            });
        }

        const response = await fetch(
            `${url}/rest/v1/rpc/increment_total_visits`,
            {
                method: "POST",

                headers: {
                    "apikey": key,
                    "Authorization": `Bearer ${key}`,
                    "Content-Type": "application/json"
                }
            }
        );

        const text = await response.text();

        console.log(
            "Supabase status:",
            response.status
        );

        console.log(
            "Supabase response:",
            text
        );

        if (!response.ok) {

            return res.status(500).json({
                error: "Supabase RPC failed",
                status: response.status
            });
        }

        const total = Number(text);

        return res.status(200).json({
            total: total
        });

    } catch (error) {

        console.error(
            "Visit API error:",
            error
        );

        return res.status(500).json({
            error: "Server error"
        });
    }
}