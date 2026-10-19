import { useState, useCallback } from 'react'
import * as yup from 'yup'

export function useFormValidation<T extends Record<string, any>>(
  initialValues: T,
  schema: yup.ObjectSchema<any>
) {
  const [values, setValues] = useState<T>(initialValues)
  const [errors, setErrors] = useState<Partial<Record<keyof T, string>>>({})
  const [touched, setTouched] = useState<Partial<Record<keyof T, boolean>>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleChange = useCallback((field: keyof T, val: any) => {
    setValues((prev) => ({ ...prev, [field]: val }))
  }, [])

  const handleBlur = useCallback(
    async (field: keyof T) => {
      setTouched((prev) => ({ ...prev, [field]: true }))
      try {
        await schema.validateAt(field as string, values)
        setErrors((prev) => {
          const next = { ...prev }
          delete next[field]
          return next
        })
      } catch (err) {
        if (err instanceof yup.ValidationError) {
          setErrors((prev) => ({ ...prev, [field]: err.message }))
        }
      }
    },
    [schema, values]
  )

  const validateAll = useCallback(async (): Promise<boolean> => {
    const allTouched: Partial<Record<keyof T, boolean>> = {}
    Object.keys(values).forEach((k) => {
      allTouched[k as keyof T] = true
    })
    setTouched(allTouched)

    try {
      await schema.validate(values, { abortEarly: false })
      setErrors({})
      return true
    } catch (err) {
      if (err instanceof yup.ValidationError) {
        const formErrors: Partial<Record<keyof T, string>> = {}
        err.inner.forEach((validationErr) => {
          if (validationErr.path) {
            formErrors[validationErr.path as keyof T] = validationErr.message
          }
        })
        setErrors(formErrors)
      }
      return false
    }
  }, [schema, values])

  const resetForm = useCallback(() => {
    setValues(initialValues)
    setErrors({})
    setTouched({})
    setIsSubmitting(false)
  }, [initialValues])

  return {
    values,
    setValues,
    errors,
    touched,
    isSubmitting,
    setIsSubmitting,
    handleChange,
    handleBlur,
    validateAll,
    resetForm,
  }
}
