/*
  # Create pending_payments table for payment reminder emails

  1. New Tables
    - `pending_payments`
      - `id` (uuid, primary key)
      - `user_id` (text, not null) - the user who has a pending payment
      - `user_email` (text, not null) - email to send reminders to
      - `book_title` (text) - title of the book being purchased
      - `amount_inr` (integer) - payment amount
      - `product_type` (text) - 'pdf' or 'print'
      - `template_id` (text) - template identifier if applicable
      - `child_name` (text) - name used in the book
      - `payment_link_id` (text) - Cashfree payment link ID
      - `payment_link_url` (text) - URL for the payment
      - `reminder_1h_sent` (boolean, default false) - whether 1-hour reminder was sent
      - `reminder_9h_sent` (boolean, default false) - whether 9-hour reminder was sent
      - `reminder_24h_sent` (boolean, default false) - whether 24-hour reminder was sent
      - `paid` (boolean, default false) - whether payment was completed
      - `created_at` (timestamptz, default now())
      - `paid_at` (timestamptz) - when payment was confirmed

  2. Security
    - Enable RLS on `pending_payments` table
    - Add policy for authenticated users to read/insert their own pending payments
*/

CREATE TABLE IF NOT EXISTS pending_payments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL,
  user_email text NOT NULL,
  book_title text DEFAULT '',
  amount_inr integer NOT NULL DEFAULT 0,
  product_type text DEFAULT 'pdf',
  template_id text DEFAULT '',
  child_name text DEFAULT '',
  payment_link_id text DEFAULT '',
  payment_link_url text DEFAULT '',
  reminder_1h_sent boolean DEFAULT false,
  reminder_9h_sent boolean DEFAULT false,
  reminder_24h_sent boolean DEFAULT false,
  paid boolean DEFAULT false,
  created_at timestamptz DEFAULT now(),
  paid_at timestamptz
);

ALTER TABLE pending_payments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own pending payments"
  ON pending_payments
  FOR SELECT
  TO authenticated
  USING (auth.uid()::text = user_id);

CREATE POLICY "Users can insert own pending payments"
  ON pending_payments
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid()::text = user_id);

CREATE POLICY "Users can update own pending payments"
  ON pending_payments
  FOR UPDATE
  TO authenticated
  USING (auth.uid()::text = user_id)
  WITH CHECK (auth.uid()::text = user_id);
