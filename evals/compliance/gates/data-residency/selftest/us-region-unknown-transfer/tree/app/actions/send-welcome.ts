"use server"

import { Resend } from "resend"

const resend = new Resend(process.env.RESEND_API_KEY)

export async function sendWelcome(to: string, name: string) {
  return resend.emails.send({ from: "hello@example.test", to, subject: "Welcome", text: `Hi ${name}` })
}
