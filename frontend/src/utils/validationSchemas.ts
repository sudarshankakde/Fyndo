import * as yup from 'yup'

// Phone login schema (10-digit Indian mobile)
export const phoneLoginSchema = yup.object().shape({
  phone: yup
    .string()
    .required('Mobile number is required')
    .matches(/^[6-9]\d{9}$/, 'Enter a valid 10-digit Indian mobile number starting with 6-9'),
})

// OTP schema (6 digits numeric)
export const otpSchema = yup.object().shape({
  otp: yup
    .string()
    .required('Verification code is required')
    .matches(/^\d{6}$/, 'Enter the complete 6-digit verification code'),
})

// Store Profile schema
export const storeProfileSchema = yup.object().shape({
  name: yup
    .string()
    .required('Store name is required')
    .min(3, 'Store name must be at least 3 characters')
    .max(50, 'Store name cannot exceed 50 characters'),
  sector: yup
    .string()
    .required('Please select a retail sector')
    .oneOf(['FOOD', 'CLOTHES_FASHION', 'ELECTRONICS', 'FOOTWEAR', 'PROPERTY'], 'Select a valid sector'),
  address: yup
    .string()
    .required('Street address is required')
    .min(5, 'Address must be at least 5 characters')
    .max(100, 'Address cannot exceed 100 characters'),
  city: yup
    .string()
    .required('City is required')
    .oneOf(['Nagpur', 'Mumbai'], 'Pilot is currently live in Nagpur and Mumbai only'),
  phone: yup
    .string()
    .required('Store contact number is required')
    .matches(/^[6-9]\d{9}$/, 'Enter a valid 10-digit mobile number'),
})

// Offer / Reel creation schema with sector-governed expiry
export const offerCreateSchema = yup.object().shape({
  title: yup
    .string()
    .required('Offer title is required')
    .min(5, 'Title must be at least 5 characters')
    .max(60, 'Title cannot exceed 60 characters'),
  description: yup
    .string()
    .max(200, 'Description cannot exceed 200 characters')
    .optional(),
  sector: yup
    .string()
    .required('Select a sector')
    .oneOf(['FOOD', 'CLOTHES_FASHION', 'ELECTRONICS', 'FOOTWEAR', 'PROPERTY']),
  discountType: yup
    .string()
    .required('Select discount type')
    .oneOf(['PERCENTAGE', 'FLAT']),
  discountValue: yup
    .number()
    .typeError('Enter a valid number')
    .required('Discount value is required')
    .positive('Discount must be greater than 0')
    .when('discountType', {
      is: 'PERCENTAGE',
      then: (schema) => schema.max(90, 'Percentage discount cannot exceed 90%'),
      otherwise: (schema) => schema.max(10000, 'Discount amount cannot exceed ₹10,000'),
    }),
  minBillAmount: yup
    .number()
    .typeError('Enter a valid number')
    .required('Minimum bill amount is required')
    .min(0, 'Minimum bill cannot be negative'),
  validityDays: yup
    .number()
    .typeError('Enter days')
    .required('Offer validity period is required')
    .min(1, 'Validity must be at least 1 day')
    .when('sector', {
      is: 'FOOD',
      then: (schema) => schema.max(5, 'Food offers can only be valid for 2–5 days'),
      otherwise: (schema) =>
        schema.when('sector', {
          is: (val: string) => ['CLOTHES_FASHION', 'ELECTRONICS', 'FOOTWEAR'].includes(val),
          then: (s) => s.max(15, 'Fashion & Electronics offers can only be valid up to 15 days'),
          otherwise: (s) => s.max(60, 'Offers can be valid up to 60 days max'),
        }),
    }),
})

// Counter Cashier PIN schema
export const cashierPinSchema = yup.object().shape({
  staffName: yup
    .string()
    .required('Staff member name is required')
    .min(2, 'Name must be at least 2 characters')
    .max(30, 'Name cannot exceed 30 characters'),
  pin: yup
    .string()
    .required('6-digit PIN is required')
    .matches(/^\d{6}$/, 'PIN must be exactly 6 numeric digits'),
})
