// Skeleton for app/showcase/page.tsx (MUI flow).
// Replace SAMPLE_* arrays with values from the parsed DESIGN.md.
"use client";

import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Container,
  Stack,
  TextField,
  Typography,
  useTheme,
} from "@mui/material";

const TYPE_VARIANTS = [
  // { variant: "h1", label: "headline-xl" },
  // { variant: "h2", label: "headline-lg" },
  // { variant: "h3", label: "headline-md" },
  // { variant: "body1", label: "body-lg" },
  // { variant: "body2", label: "body-md" },
  // { variant: "button", label: "label-md" },
] as const;

export default function Showcase() {
  const theme = useTheme();

  // Build swatches from theme.palette so any change to theme.ts is reflected.
  const swatches: { name: string; bg: string; fg?: string }[] = [
    { name: "primary",         bg: theme.palette.primary.main,    fg: theme.palette.primary.contrastText },
    { name: "secondary",       bg: theme.palette.secondary.main,  fg: theme.palette.secondary.contrastText },
    // { name: "tertiary",     bg: theme.palette.tertiary.main,   fg: theme.palette.tertiary.contrastText },
    { name: "error",           bg: theme.palette.error.main,      fg: theme.palette.error.contrastText },
    { name: "background",      bg: theme.palette.background.default, fg: theme.palette.text.primary },
    { name: "background.paper",bg: theme.palette.background.paper,   fg: theme.palette.text.primary },
    // { name: "surfaceContainer.high", bg: theme.palette.surfaceContainer.high, fg: theme.palette.text.primary },
  ];

  return (
    <Container maxWidth={false} sx={{ maxWidth: theme.layout?.containerMax ?? 1280, py: 8 }}>
      <Stack spacing={6}>
        <Box>
          <Typography variant="h1" gutterBottom>Design system showcase</Typography>
          <Typography variant="body1" color="text.secondary">
            Generated from DESIGN.md. Use this page to verify tokens render correctly.
          </Typography>
        </Box>

        <Box>
          <Typography variant="h3" gutterBottom>Colors</Typography>
          <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 2 }}>
            {swatches.map((s) => (
              <Box
                key={s.name}
                sx={{
                  bgcolor: s.bg,
                  color: s.fg,
                  height: 96,
                  borderRadius: theme.radius?.md ?? 1,
                  p: 1.5,
                  display: "flex",
                  alignItems: "flex-end",
                  fontFamily: "monospace",
                  fontSize: 12,
                  border: `1px solid ${theme.palette.divider}`,
                }}
              >
                {s.name}
              </Box>
            ))}
          </Box>
        </Box>

        <Box>
          <Typography variant="h3" gutterBottom>Typography</Typography>
          <Stack spacing={3}>
            {TYPE_VARIANTS.map((v) => (
              <Box key={v.label}>
                <Typography variant="caption" color="text.secondary" sx={{ fontFamily: "monospace" }}>
                  {v.label} → MuiTypography variant="{v.variant}"
                </Typography>
                <Typography variant={v.variant as any}>The quick brown fox jumps over the lazy dog</Typography>
              </Box>
            ))}
          </Stack>
        </Box>

        <Box>
          <Typography variant="h3" gutterBottom>Components</Typography>
          <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap>
            <Button variant="contained">Primary</Button>
            <Button variant="outlined">Secondary</Button>
            <Button variant="text">Text</Button>
            <Chip label="Default" />
            {/* <Chip label="Celestial" variant="celestial" /> */}
          </Stack>
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 3, mt: 3 }}>
            <Card>
              <CardContent>
                <Typography variant="h5" gutterBottom>Card</Typography>
                <Typography variant="body2" color="text.secondary">
                  Themed surface from MuiCard styleOverrides.
                </Typography>
              </CardContent>
            </Card>
            <Card>
              <CardContent>
                <TextField label="Email" placeholder="you@example.com" />
              </CardContent>
            </Card>
          </Box>
        </Box>
      </Stack>
    </Container>
  );
}
