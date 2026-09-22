"use client"

import { Switch } from "@headlessui/react"
import { useState } from "react"

export default function NotificationSettingsPage() {
  const [digest, setDigest] = useState(false)
  return (
    <form className="mx-auto max-w-lg space-y-4 p-6">
      <label htmlFor="email">Email address</label>
      <input id="email" type="email" className="w-full rounded border px-3 py-2" />
      <Switch checked={digest} onChange={setDigest} />
      <button type="submit" className="rounded bg-black px-4 py-2 text-white">Save</button>
    </form>
  )
}
