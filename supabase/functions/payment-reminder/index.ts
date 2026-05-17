import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { MongoClient } from "npm:mongodb@6.8.0";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers":
    "Content-Type, Authorization, X-Client-Info, Apikey",
};

interface PendingPayment {
  _id: string;
  user_email: string;
  child_name: string;
  book_title: string;
  amount_inr: number;
  payment_link_url: string;
  reminder_1h_sent: boolean;
  reminder_9h_sent: boolean;
  reminder_24h_sent: boolean;
  paid: boolean;
  created_at: Date;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 200, headers: corsHeaders });
  }

  try {
    const mongoUri = Deno.env.get("MONGODB_URI");
    if (!mongoUri) {
      return new Response(
        JSON.stringify({ error: "MONGODB_URI not configured" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const resendKey = Deno.env.get("RESEND_API_KEY");
    const dbName = Deno.env.get("MONGODB_DB") || "children_book_generator";

    const client = new MongoClient(mongoUri);
    await client.connect();
    const db = client.db(dbName);
    const collection = db.collection<PendingPayment>("pending_payments");

    const now = new Date();

    // Fetch all unpaid pending payments
    const pending = await collection.find({ paid: false }).toArray();

    let emailsSent = 0;

    for (const payment of pending) {
      const createdAt = new Date(payment.created_at);
      const hoursSinceCreation =
        (now.getTime() - createdAt.getTime()) / (1000 * 60 * 60);

      let shouldSendReminder = false;
      let reminderField = "";
      let reminderSubject = "";
      let reminderBody = "";

      if (hoursSinceCreation >= 1 && !payment.reminder_1h_sent) {
        shouldSendReminder = true;
        reminderField = "reminder_1h_sent";
        reminderSubject = `${payment.child_name}'s storybook is almost ready!`;
        reminderBody = buildEmailBody(payment, "1hour");
      } else if (hoursSinceCreation >= 9 && !payment.reminder_9h_sent) {
        shouldSendReminder = true;
        reminderField = "reminder_9h_sent";
        reminderSubject = `Don't forget ${payment.child_name}'s personalized book!`;
        reminderBody = buildEmailBody(payment, "9hour");
      } else if (hoursSinceCreation >= 24 && !payment.reminder_24h_sent) {
        shouldSendReminder = true;
        reminderField = "reminder_24h_sent";
        reminderSubject = `Last chance: ${payment.child_name}'s storybook expires soon`;
        reminderBody = buildEmailBody(payment, "24hour");
      }

      if (shouldSendReminder && payment.user_email) {
        const emailSent = await sendReminderEmail(
          resendKey,
          payment.user_email,
          reminderSubject,
          reminderBody
        );

        if (emailSent) {
          await collection.updateOne(
            { _id: payment._id },
            { $set: { [reminderField]: true } }
          );
          emailsSent++;
        }
      }
    }

    await client.close();

    return new Response(
      JSON.stringify({
        message: `Processed ${pending.length} pending payments, sent ${emailsSent} reminders`,
      }),
      { headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  } catch (err) {
    return new Response(
      JSON.stringify({ error: String(err) }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});

function buildEmailBody(
  payment: PendingPayment,
  stage: "1hour" | "9hour" | "24hour"
): string {
  const paymentUrl = payment.payment_link_url || "#";
  const childName = payment.child_name || "your child";
  const amount = payment.amount_inr;

  const messages: Record<string, string> = {
    "1hour": `
      <h2>Your storybook is almost ready!</h2>
      <p>Hi there,</p>
      <p>The amazing personalized storybook for <strong>${childName}</strong> is waiting for you.
      We have already generated beautiful preview pages -- just complete your payment to unlock the full book.</p>
      <p><a href="${paymentUrl}" style="display:inline-block;background:#2563eb;color:white;padding:12px 28px;border-radius:8px;font-weight:700;text-decoration:none;">Complete Payment (Rs.${amount})</a></p>
      <p>Your child will love seeing themselves as the hero of their very own story!</p>
    `,
    "9hour": `
      <h2>${childName}'s storybook is still waiting!</h2>
      <p>Hi there,</p>
      <p>We noticed you haven't completed the payment for <strong>${childName}</strong>'s personalized storybook yet.
      The book is ready and the beautiful AI-generated illustrations are waiting to be unlocked.</p>
      <p><a href="${paymentUrl}" style="display:inline-block;background:#2563eb;color:white;padding:12px 28px;border-radius:8px;font-weight:700;text-decoration:none;">Unlock the Full Book (Rs.${amount})</a></p>
      <p>Don't miss out -- this will be a treasured keepsake for years to come.</p>
    `,
    "24hour": `
      <h2>Last reminder: ${childName}'s book expires soon</h2>
      <p>Hi there,</p>
      <p>This is our final reminder about the personalized storybook for <strong>${childName}</strong>.
      The payment link will expire soon, and you'll need to start over if you don't complete it now.</p>
      <p><a href="${paymentUrl}" style="display:inline-block;background:#dc2626;color:white;padding:12px 28px;border-radius:8px;font-weight:700;text-decoration:none;">Complete Payment Now (Rs.${amount})</a></p>
      <p>The story is ready. The illustrations are waiting. All it takes is one click.</p>
    `,
  };

  return `
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px;">
      ${messages[stage]}
      <hr style="margin:24px 0;border:none;border-top:1px solid #eee;" />
      <p style="color:#888;font-size:12px;">StoryBook Generator -- Personalized children's books</p>
    </div>
  `;
}

async function sendReminderEmail(
  resendKey: string | undefined,
  email: string,
  subject: string,
  htmlBody: string
): Promise<boolean> {
  try {
    if (!resendKey) {
      console.log(`[payment-reminder] RESEND_API_KEY not set. Would send to ${email}: ${subject}`);
      return true;
    }

    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${resendKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: "StoryBook <noreply@storybook-generator.app>",
        to: [email],
        subject: subject,
        html: htmlBody,
      }),
    });
    return res.ok;
  } catch (err) {
    console.error(`Failed to send email to ${email}:`, err);
    return false;
  }
}
