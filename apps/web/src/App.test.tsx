import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { App } from "./App";

describe("LoginPage", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/login");
  });

  it("keeps SMS submit disabled until a code is requested for the current phone", async () => {
    render(<App />);

    const continueButton = screen.getByRole("button", { name: "Continue with SMS code" });
    expect(continueButton).toBeDisabled();

    fireEvent.change(screen.getByLabelText("SMS code"), { target: { value: "123456" } });
    expect(continueButton).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByText("Development SMS code");
    fireEvent.click(screen.getByRole("button", { name: "123456" }));

    await waitFor(() => expect(continueButton).toBeEnabled());
  });

  it("keeps password sign-in disabled until the password is long enough", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Password" }));
    const signInButton = screen.getByRole("button", { name: "Sign in with password" });
    expect(signInButton).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "short" } });
    expect(signInButton).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "password123" } });
    expect(signInButton).toBeEnabled();
  });
});
