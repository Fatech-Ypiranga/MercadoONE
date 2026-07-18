"use client";

import { useEffect, useRef, useState } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { lookupCep } from "@/lib/api/cep-api";
import {
  digitsOnly,
  mergeCepSuccess,
  shouldApplyCepResult,
} from "@/lib/apply-cep-result";

export type AddressFormState = {
  description: string;
  zip_code: string;
  street: string;
  number: string;
  complement: string;
  neighborhood: string;
  city: string;
  state: string;
  ibge_code: string;
};

export const emptyAddress: AddressFormState = {
  description: "Principal",
  zip_code: "",
  street: "",
  number: "",
  complement: "",
  neighborhood: "",
  city: "",
  state: "",
  ibge_code: "",
};

export function addressPayload(form: AddressFormState) {
  return {
    description: form.description.trim() || "Principal",
    zip_code: form.zip_code.replace(/\D/g, ""),
    street: form.street.trim(),
    number: form.number.trim(),
    complement: form.complement.trim() || null,
    neighborhood: form.neighborhood.trim(),
    city: form.city.trim(),
    state: form.state.trim().toUpperCase().slice(0, 2),
    ibge_code: form.ibge_code.trim(),
  };
}

export function addressReady(form: AddressFormState) {
  const payload = addressPayload(form);
  return Boolean(
    payload.zip_code.length === 8 &&
      payload.street &&
      payload.number &&
      payload.neighborhood &&
      payload.city &&
      payload.state.length === 2 &&
      /^\d{7}$/.test(payload.ibge_code),
  );
}

export function AddressFields({
  form,
  onChange,
}: {
  form: AddressFormState;
  onChange: (next: AddressFormState) => void;
}) {
  const [cepLoading, setCepLoading] = useState(false);
  const [cepError, setCepError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastLookedUp = useRef<string>("");
  const formRef = useRef(form);
  const requestIdRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  formRef.current = form;

  const handleZipChange = (value: string) => {
    onChange({ ...formRef.current, zip_code: value });
    setCepError(null);

    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    const digits = digitsOnly(value);
    if (digits.length !== 8 || digits === lastLookedUp.current) return;

    debounceRef.current = setTimeout(async () => {
      const requestId = ++requestIdRef.current;
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setCepLoading(true);
      const result = await lookupCep(digits, controller.signal);

      if (requestId !== requestIdRef.current) {
        return;
      }

      setCepLoading(false);

      if (
        !shouldApplyCepResult({
          requestId,
          latestRequestId: requestIdRef.current,
          lookedUpDigits: digits,
          currentZipCode: formRef.current.zip_code,
        })
      ) {
        return;
      }

      if (result.status === "aborted") {
        return;
      }

      lastLookedUp.current = digits;

      if (result.status === "success") {
        onChange(mergeCepSuccess(formRef.current, result.data));
        setCepError(null);
      } else {
        setCepError(result.message);
      }
    }, 300);
  };

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      abortRef.current?.abort();
    };
  }, []);

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="space-y-1.5 sm:col-span-2">
        <Label>Descrição</Label>
        <Input
          value={form.description}
          onChange={(e) => onChange({ ...form, description: e.target.value })}
          placeholder="Principal"
        />
      </div>
      <div className="space-y-1.5">
        <Label>CEP</Label>
        <div className="relative">
          <Input
            value={form.zip_code}
            onChange={(e) => handleZipChange(e.target.value)}
            placeholder="00000-000"
            className={cepLoading ? "opacity-60" : undefined}
          />
          {cepLoading && (
            <span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-muted-foreground animate-pulse">
              Consultando…
            </span>
          )}
        </div>
        {cepError ? (
          <p className="text-xs text-destructive">{cepError}</p>
        ) : null}
      </div>
      <div className="space-y-1.5">
        <Label>UF</Label>
        <Input
          maxLength={2}
          value={form.state}
          onChange={(e) => onChange({ ...form, state: e.target.value })}
        />
      </div>
      <div className="space-y-1.5 sm:col-span-2">
        <Label>Rua</Label>
        <Input
          value={form.street}
          onChange={(e) => onChange({ ...form, street: e.target.value })}
        />
      </div>
      <div className="space-y-1.5">
        <Label>Número</Label>
        <Input
          value={form.number}
          onChange={(e) => onChange({ ...form, number: e.target.value })}
        />
      </div>
      <div className="space-y-1.5">
        <Label>Complemento</Label>
        <Input
          value={form.complement}
          onChange={(e) => onChange({ ...form, complement: e.target.value })}
        />
      </div>
      <div className="space-y-1.5">
        <Label>Bairro</Label>
        <Input
          value={form.neighborhood}
          onChange={(e) => onChange({ ...form, neighborhood: e.target.value })}
        />
      </div>
      <div className="space-y-1.5">
        <Label>Cidade</Label>
        <Input
          value={form.city}
          onChange={(e) => onChange({ ...form, city: e.target.value })}
        />
      </div>
      <div className="space-y-1.5">
        <Label>Código IBGE</Label>
        <Input
          inputMode="numeric"
          maxLength={7}
          value={form.ibge_code}
          onChange={(e) => onChange({ ...form, ibge_code: e.target.value })}
        />
      </div>
    </div>
  );
}
