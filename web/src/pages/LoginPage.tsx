import { Link } from 'react-router-dom'
import { SignIn } from '@clerk/clerk-react'
import { Image } from 'lucide-react'

export function LoginPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 py-12 px-4">
      <div className="mb-6 flex flex-col items-center text-center">
        <Image className="w-12 h-12 text-primary-600" />
        <h1 className="mt-4 text-2xl font-bold text-gray-900">Pixiserve</h1>
        <p className="mt-2 text-sm text-gray-600">
          Need an account?{' '}
          <Link to="/register" className="text-primary-600 hover:text-primary-500 font-medium">
            Sign up
          </Link>
        </p>
      </div>
      <SignIn
        path="/login"
        routing="path"
        signUpUrl="/register"
        appearance={{
          elements: {
            rootBox: 'mx-auto',
            card: 'shadow-lg',
          },
        }}
      />
    </div>
  )
}
