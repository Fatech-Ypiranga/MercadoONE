"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { login } from "@/lib/api/auth-api";
import { ApiError } from "@/lib/api/client";

const loginSchema = z.object({
  company_document: z.string().min(1, "Informe o CNPJ da empresa"),
  login: z.string().min(1, "Informe e-mail ou usuário"),
  password: z.string().min(1, "Informe a senha"),
});

type LoginForm = z.infer<typeof loginSchema>;

export function LoginForm() {
  const { loginWithToken } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { company_document: "", login: "", password: "" },
  });

  async function onSubmit(values: LoginForm) {
    setServerError(null);
    try {
      const token = await login({
        company_document: values.company_document.replace(/\D/g, ""),
        login: values.login,
        password: values.password,
      });
      await loginWithToken(token.access_token);
    } catch (error) {
      if (error instanceof ApiError) {
        setServerError(error.message);
      } else {
        setServerError("Não foi possível conectar à API. Verifique se ela está rodando.");
      }
    }
  }

  return (
    <Card className="w-full max-w-md border-border/80 shadow-sm">
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl font-semibold tracking-tight">PyERP</CardTitle>
        <CardDescription>
          Entre com o CNPJ da empresa, e-mail ou usuário e senha.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className="space-y-2">
            <Label htmlFor="company_document">CNPJ da empresa</Label>
            <Input
              id="company_document"
              autoComplete="organization"
              placeholder="00.000.000/0001-91"
              aria-invalid={Boolean(errors.company_document)}
              {...register("company_document")}
            />
            {errors.company_document ? (
              <p className="text-sm text-destructive">{errors.company_document.message}</p>
            ) : null}
          </div>

          <div className="space-y-2">
            <Label htmlFor="login">E-mail ou usuário</Label>
            <Input
              id="login"
              autoComplete="username"
              placeholder="admin@pyerp.local"
              aria-invalid={Boolean(errors.login)}
              {...register("login")}
            />
            {errors.login ? (
              <p className="text-sm text-destructive">{errors.login.message}</p>
            ) : null}
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Senha</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              aria-invalid={Boolean(errors.password)}
              {...register("password")}
            />
            {errors.password ? (
              <p className="text-sm text-destructive">{errors.password.message}</p>
            ) : null}
          </div>

          {serverError ? (
            <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {serverError}
            </p>
          ) : null}

          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Entrando…" : "Entrar"}
          </Button>

          <p className="text-center text-sm text-muted-foreground">
            Nova empresa?{" "}
            <Link href="/cadastro" className="font-medium underline">
              Solicitar cadastro
            </Link>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
