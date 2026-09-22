"use client"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"

export default function NotificationSettingsPage() {
  return (
    <Card className="mx-auto max-w-lg">
      <CardHeader>
        <CardTitle>Notifications</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid gap-2">
          <Label htmlFor="email">Email address</Label>
          <Input id="email" type="email" />
        </div>
        <div className="flex items-center justify-between">
          <Label htmlFor="digest">Weekly digest</Label>
          <Switch id="digest" />
        </div>
      </CardContent>
      <CardFooter>
        <Button type="submit">Save</Button>
      </CardFooter>
    </Card>
  )
}
