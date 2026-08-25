export default async function handler(req, res) {
  // CORS
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    return res.status(200).end();
  }

  if (req.method !== "GET") {
    return res.status(405).json({
      success: false,
      message: "Method not allowed"
    });
  }

  const roll = String(req.query.roll || "").trim();

  if (!roll) {
    return res.status(400).json({
      success: false,
      message: "Roll number is required."
    });
  }

  // Only numeric roll numbers
  if (!/^\d+$/.test(roll)) {
    return res.status(400).json({
      success: false,
      message: "Invalid roll number."
    });
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SUPABASE_KEY = process.env.SUPABASE_KEY;

  if (!SUPABASE_URL || !SUPABASE_KEY) {
    console.error("Missing SUPABASE_URL or SUPABASE_KEY");

    return res.status(500).json({
      success: false,
      message: "Server configuration error."
    });
  }

  try {
    const url =
      `${SUPABASE_URL}/rest/v1/students` +
      `?select=id,roll,name,board,group_name,session,type,institute,district,result,gpa,total_score,subjects,father_name,mother_name,reg_no,date_of_birth,group` +
      `&roll=eq.${encodeURIComponent(roll)}` +
      `&limit=1`;

    const response = await fetch(url, {
      method: "GET",
      headers: {
        apikey: SUPABASE_KEY,
        Authorization: `Bearer ${SUPABASE_KEY}`,
        "Content-Type": "application/json"
      }
    });

    if (!response.ok) {
      const errorText = await response.text();

      console.error("Supabase error:", errorText);

      return res.status(500).json({
        success: false,
        message: "Unable to fetch result."
      });
    }

    const data = await response.json();

    if (!data || data.length === 0) {
      return res.status(404).json({
        success: false,
        message: `No result found for roll ${roll}.`
      });
    }

    const student = data[0];

    // Normalize subjects
    let subjects = student.subjects;

    if (typeof subjects === "string") {
      try {
        subjects = JSON.parse(subjects);
      } catch {
        subjects = [];
      }
    }

    if (!Array.isArray(subjects)) {
      subjects = [];
    }

    return res.status(200).json({
      success: true,
      student: {
        id: student.id,
        roll: student.roll,
        name: student.name,
        board: student.board,
        group_name: student.group_name || student.group,
        session: student.session,
        type: student.type,
        institute: student.institute,
        district: student.district,
        result: student.result,
        gpa: student.gpa,
        total_score: student.total_score,
        subjects,
        father_name: student.father_name,
        mother_name: student.mother_name,
        reg_no: student.reg_no,
        date_of_birth: student.date_of_birth
      }
    });

  } catch (error) {
    console.error("Result API error:", error);

    return res.status(500).json({
      success: false,
      message: "Internal server error."
    });
  }
}