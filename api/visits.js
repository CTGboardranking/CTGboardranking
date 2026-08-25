export default async function handler(req, res) {

    if (req.method !== "POST") {
        return res.status(405).json({
            error: "Method not allowed"
        });
    }

    try {

        const response = await fetch(
            `${process.env.SUPABASE_URL}/rest/v1/rpc/increment_total_visits`,
            {
                method: "POST",

                headers: {
                    "apikey": process.env.SUPABASE_KEY,
                    "Authorization":
                        `Bearer ${process.env.SUPABASE_KEY}`,
                    "Content-Type": "application/json"
                }
            }
        );

        if (!response.ok) {

            const error =
                await response.text();

            console.error(
                "Supabase error:",
                error
            );

            return res.status(500).json({
                error: "Failed to update visits"
            });
        }

        const total =
            await response.json();

        return res.status(200).json({
            total: Number(total)
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